import asyncio
import base64
import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langgraph.checkpoint.memory import InMemorySaver

from app.api.routes import files
from app.services import image_storage
from app.services.middleware.image_paths import ImagePathMiddleware
from app.services.tools import callback

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l1cAAAAASUVORK5CYII=')
DATA_IMAGE = 'data:image/png;base64,' + base64.b64encode(PNG).decode()


@pytest.fixture
def image_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(image_storage, 'get_temp_dir', lambda: tmp_path)
    return tmp_path


def test_office_image_endpoint_saves_bytes_and_reuses_identical_pictures(image_dir):
    app = FastAPI()
    app.include_router(files.router, prefix='/api/chat')
    with TestClient(app) as client:
        first = client.post('/api/chat/image', files={'file': ('word.png', PNG, 'image/png')})
        second = client.post('/api/chat/image', files={'file': ('word.png', PNG, 'image/png')})
        assert first.status_code == 200
        assert first.json() == second.json()
        assert first.json()['project_path'].startswith('temp/')
        assert DATA_IMAGE not in first.text
        assert (image_dir / first.json()['project_path'].split('/')[-1]).read_bytes() == PNG
        assert client.post('/api/chat/image', files={'file': ('word.png', b'', 'image/png')}).status_code == 400
        assert client.post('/api/chat/image', files={'file': ('word.txt', b'not an image', 'text/plain')}).status_code == 400


def test_frontend_document_response_converts_images_in_body_tables_and_search_results(image_dir):
    async def run():
        chat_id = 'image-response'
        queue = callback.create_tool_request(chat_id)
        try:
            await callback.submit_tool_response(chat_id, {
                'type': 'document_response',
                'documentJson': {'paragraphs': [
                    {'runs': [{'url': DATA_IMAGE, 'width': 12}]},
                    {'tables': [{'cells': [[{'paragraphs': [{'runs': [{'url': DATA_IMAGE}]}]}]]}]}
                ]},
                'matches': [{'paragraph': {'runs': [{'url': DATA_IMAGE}]}}]
            })
            result = queue.get_nowait()
            assert DATA_IMAGE not in json.dumps(result)
            image = result['documentJson']['paragraphs'][0]['runs'][0]
            assert image['width'] == 12
            assert image['url'].endswith('.png')
            assert len(list(image_dir.iterdir())) == 1
        finally:
            callback.cleanup_tool_request(chat_id)
    asyncio.run(run())


def test_history_is_rewritten_before_model_use_including_tool_json_and_vision_blocks(image_dir):
    document = {'paragraphs': [{'runs': [{'url': DATA_IMAGE, 'altText': 'keep description'}]}]}
    messages = [
        HumanMessage(id='human', content=[{'type': 'image_url', 'image_url': {'url': DATA_IMAGE}}]),
        AIMessage(id='ai', content='', tool_calls=[{'name': 'edit_document', 'id': 'call', 'args': document}]),
        ToolMessage(id='tool', tool_call_id='call', content=json.dumps(document))
    ]
    result = ImagePathMiddleware().before_model({'messages': messages}, None)
    rewritten = result['messages'][1:]
    assert [message.id for message in rewritten] == ['human', 'ai', 'tool']
    assert rewritten[2].tool_call_id == 'call'
    assert rewritten[0].content[0]['type'] == 'text'
    assert DATA_IMAGE not in json.dumps([message.model_dump() for message in rewritten])
    assert json.loads(rewritten[2].content)['paragraphs'][0]['runs'][0]['altText'] == 'keep description'
    assert len(list(image_dir.iterdir())) == 1
    assert ImagePathMiddleware().before_model({'messages': rewritten}, None) is None


def test_agent_model_and_checkpoint_receive_only_image_paths(image_dir):
    captured = []

    class PathOnlyModel(FakeMessagesListChatModel):
        def _generate(self, messages, **kwargs):
            captured.extend(messages)
            return super()._generate(messages, **kwargs)

    checkpoint = InMemorySaver()
    graph = create_agent(PathOnlyModel(responses=[AIMessage(content='image path received')]),
                         middleware=[ImagePathMiddleware()], checkpointer=checkpoint)
    config = {'configurable': {'thread_id': 'image-checkpoint'}}
    graph.invoke({'messages': [HumanMessage(content=[{'type': 'image_url', 'image_url': {'url': DATA_IMAGE}}])]}, config)
    assert DATA_IMAGE not in json.dumps([message.model_dump() for message in captured])
    assert captured[0].content[0]['type'] == 'text'
    saved = graph.get_state(config).values['messages']
    assert DATA_IMAGE not in json.dumps([message.model_dump() for message in saved])


def test_invalid_frontend_image_returns_an_error_instead_of_inline_data(image_dir):
    async def run():
        chat_id = 'invalid-image-response'
        queue = callback.create_tool_request(chat_id)
        try:
            await callback.submit_tool_response(chat_id, {'type': 'document_response', 'documentJson': {
                'paragraphs': [{'runs': [{'url': 'data:image/png;base64,%%%'}]}]
            }})
            result = queue.get_nowait()
            assert result['success'] is False
            assert 'data:image' not in json.dumps(result)
            assert 'documentJson' not in result
        finally:
            callback.cleanup_tool_request(chat_id)
    asyncio.run(run())
