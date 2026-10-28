import asyncio
import json
import threading
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.api.routes import chat
from app.services.agent import agent
from app.services.tools import callback


def turn(**overrides):
    return {
        "type": "chat", "chatId": str(uuid.uuid4()), "sessionId": str(uuid.uuid4()),
        "windowId": str(uuid.uuid4()), "message": "work", **overrides,
    }


def reply(request, **fields):
    return {"chatId": request["chatId"], "sessionId": request["sessionId"], **fields}


def receive_done(socket):
    events = []
    while True:
        event = socket.receive_json()
        events.append(event)
        if event["type"] == "done":
            return events


@pytest.fixture
def server(monkeypatch):
    persisted = []

    async def stream(**kwargs):
        # Identical request IDs across two chats must still route independently.
        yield 'data: {"type":"edit_document","requestId":"same-tool-call"}\n\n'
        result = await callback.wait_for_tool_response(kwargs["chat_id"], "same-tool-call", timeout=3)
        yield f'data: {json.dumps({"type": "text", "content": result["content"]})}\n\n'
        yield "data: [DONE]\n\n"

    async def persist(**kwargs):
        persisted.append(kwargs)

    monkeypatch.setattr(chat, "single_agent_stream", stream)
    monkeypatch.setattr(chat, "_persist_chat_turn", persist)
    monkeypatch.setattr(chat, "record_token_usage", AsyncMock())
    monkeypatch.setattr(chat, "_extract_long_term_memory_sync", lambda *args: None)
    app = FastAPI()
    app.include_router(chat.router, prefix="/api/chat")
    app.state.checkpointer = SimpleNamespace(aget_tuple=AsyncMock(return_value=None))
    app.state.memory_tasks = set()
    with TestClient(app) as client:
        yield client, persisted
    assert not chat._active_chats
    assert not chat._active_sessions
    assert not chat._active_windows


def test_two_windows_stream_and_route_tool_results_independently(server):
    client, persisted = server
    a, b = turn(), turn()
    with client.websocket_connect('/api/chat/ws') as wa, client.websocket_connect('/api/chat/ws') as wb:
        wa.send_json(a)
        assert wa.receive_json()['chatId'] == a['chatId']
        wb.send_json(b)
        assert wb.receive_json()['chatId'] == b['chatId']  # A is still waiting.
        wb.send_json(reply(b, type='edit_document_response', requestId='same-tool-call', content='B only'))
        assert receive_done(wb)[0]['content'] == 'B only'
        assert [row['session_id'] for row in persisted] == [b['sessionId']]
        # Cross-chat tool replies and stop commands cannot terminate A.
        wa.send_json(reply(b, type='stop'))
        wa.send_json(reply(b, type='edit_document_response', requestId='same-tool-call', content='wrong'))
        wa.send_json(reply(a, type='edit_document_response', requestId='same-tool-call', content='A only'))
        assert receive_done(wa)[0]['content'] == 'A only'
    assert [(row['session_id'], row['assistant_content']) for row in persisted] == [
        (b['sessionId'], 'B only'), (a['sessionId'], 'A only')]


@pytest.mark.parametrize('disconnect', [False, True])
def test_stopping_one_window_does_not_cancel_another(server, disconnect):
    client, _ = server
    a, b = turn(), turn()
    with client.websocket_connect('/api/chat/ws') as wb:
        with client.websocket_connect('/api/chat/ws') as wa:
            wa.send_json(a)
            wa.receive_json()
            wb.send_json(b)
            wb.receive_json()
            if not disconnect:
                wa.send_json(reply(a, type='stop'))
                assert receive_done(wa)[-1]['chatId'] == a['chatId']
        wb.send_json(reply(b, type='edit_document_response', requestId='same-tool-call', content='still running'))
        assert receive_done(wb)[0]['content'] == 'still running'


@pytest.mark.parametrize('conflict', ['window', 'session', 'connection'])
def test_duplicate_turn_is_rejected_without_canceling_original(server, conflict):
    client, _ = server
    a = turn()
    b = turn(**({'windowId': a['windowId']} if conflict != 'session' else {'sessionId': a['sessionId']}))
    with client.websocket_connect('/api/chat/ws') as wa, client.websocket_connect('/api/chat/ws') as wb:
        wa.send_json(a)
        wa.receive_json()
        other = wa if conflict == 'connection' else wb
        other.send_json(b)
        events = receive_done(other)
        assert events[0]['type'] == 'error'
        assert events[0]['chatId'] == b['chatId']
        wa.send_json(reply(a, type='stop'))
        receive_done(wa)
        # The same window can use a different session after cancellation.
        c = turn(windowId=a['windowId'])
        wa.send_json(c)
        assert wa.receive_json()['chatId'] == c['chatId']
        wa.send_json(reply(a, type='stop'))  # Late stop for the previous turn.
        wa.send_json(reply(c, type='edit_document_response', requestId='same-tool-call', content='new turn'))
        assert receive_done(wa)[0]['content'] == 'new turn'


def test_native_async_graphs_and_sync_tools_keep_context_and_checkpoints_isolated(tmp_path, monkeypatch):
    entered = set()
    tool_contexts = []

    class Model(BaseChatModel):
        @property
        def _llm_type(self):
            return 'concurrency-test'

        def bind_tools(self, tools, **kwargs):
            return self

        def _generate(self, *args, **kwargs):
            raise AssertionError('The agent must use the asynchronous model path')

        async def _agenerate(self, messages, **kwargs):
            chat_id = callback._current_chat_id.get()
            entered.add(chat_id)
            # Neither request may finish before both models are executing.
            async with asyncio.timeout(3):
                while len(entered) < 2:
                    await asyncio.sleep(0.01)
            if messages[-1].type == 'tool':
                response = AIMessage(content=f'finished:{chat_id}')
            else:
                response = AIMessage(content='', tool_calls=[{'name': 'identify', 'args': {}, 'id': 'identify-1'}])
            return ChatResult(generations=[ChatGeneration(message=response)])

    @tool
    def identify() -> str:
        """Return this tool's request context from its worker thread."""
        context = (callback._current_chat_id.get(), callback._current_request_context.get())
        tool_contexts.append(context)
        return context[0]

    monkeypatch.setattr(agent, 'resolve_model', lambda *args: 'fake')
    monkeypatch.setattr(agent, 'init_chat_model_with_reasoning', lambda *args, **kwargs: Model())
    monkeypatch.setattr(agent, 'load_mcp_tools', AsyncMock(return_value=([], [], [])))
    monkeypatch.setattr(agent, 'get_base_tools_for_mode', lambda mode: [identify])
    monkeypatch.setattr(agent, 'build_skills_prompt', lambda: '')
    from app.services import memory, llm_client
    monkeypatch.setattr(memory, 'is_long_term_memory_enabled', lambda: False)
    monkeypatch.setattr(llm_client, 'get_custom_prompt', lambda: '')

    async def run():
        async with AsyncSqliteSaver.from_conn_string(str(tmp_path / 'concurrent.db')) as saver:
            async def collect(name):
                return ''.join([part async for part in agent.process_writing_request_stream(
                    message=name, model='fake', chat_id=name, session_id=name, checkpointer=saver,
                    document_meta={'documentId': 1 if name == 'a' else 2, 'documentName': name},
                )])
            a, b = await asyncio.gather(collect('a'), collect('b'))
            assert 'finished:a' in a and 'finished:b' not in a
            assert 'finished:b' in b and 'finished:a' not in b
            for name in ('a', 'b'):
                checkpoint = await saver.aget_tuple(memory.build_thread_config(name))
                assert checkpoint.checkpoint['channel_values']['messages'][-1].content == f'finished:{name}'
    asyncio.run(run())
    assert {name: ctx['document_meta']['documentName'] for name, ctx in tool_contexts} == {'a': 'a', 'b': 'b'}


def test_python_tool_namespaces_are_not_shared_between_requests():
    from app.services.agent.tools import get_base_tools_for_mode
    first = next(tool for tool in get_base_tools_for_mode('agent') if tool.name == 'Python_REPL')
    second = next(tool for tool in get_base_tools_for_mode('agent') if tool.name == 'Python_REPL')
    assert first.python_repl is not second.python_repl
    first.python_repl.globals['owner'] = 'first'
    assert 'owner' not in second.python_repl.globals


def test_cancel_waits_for_native_async_stream_cleanup(monkeypatch):
    entered, closed = asyncio.Event(), []

    class Graph:
        async def astream(self, **kwargs):
            try:
                entered.set()
                await asyncio.Event().wait()
                yield None
            finally:
                closed.append(True)

    monkeypatch.setattr(agent, 'resolve_model', lambda *args: 'fake')
    monkeypatch.setattr(agent, 'init_chat_model_with_reasoning', lambda *args, **kwargs: object())
    monkeypatch.setattr(agent, 'load_mcp_tools', AsyncMock(return_value=([], [], [])))
    monkeypatch.setattr(agent, 'get_base_tools_for_mode', lambda mode: [])
    monkeypatch.setattr(agent, 'build_skills_prompt', lambda: '')
    monkeypatch.setattr(agent, 'build_agent_middleware', lambda **kwargs: [])
    monkeypatch.setattr(agent, 'create_agent', lambda **kwargs: Graph())
    from app.services import memory
    monkeypatch.setattr(memory, 'is_long_term_memory_enabled', lambda: False)

    async def collect():
        async for _ in agent.process_writing_request_stream(message='cancel', chat_id='cancel-test'):
            pass

    async def run():
        task = asyncio.create_task(collect())
        await asyncio.wait_for(entered.wait(), timeout=3)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert closed == [True]
        assert 'cancel-test' not in callback._stop_events
        assert not [t for t in asyncio.all_tasks() if t.get_name() == 'agent:cancel-test']
        callback.cleanup_tool_request('cancel-test')
    asyncio.run(run())


def test_canceled_worker_keeps_its_stop_signal_after_turn_registry_cleanup():
    async def run():
        name = 'retired-turn'
        event = threading.Event()
        callback.create_tool_request(name)
        callback.register_stop_event(name, event)
        chat_token = callback._current_chat_id.set(name)
        event_token = callback._current_stop_event.set(event)
        try:
            callback.request_stop(name)
            callback.cleanup_tool_request(name)
            callback.unregister_stop_event(name, event)
            assert name not in callback._stop_requested_sessions
            assert callback.is_stop_requested(name)
            await callback.submit_tool_response(name, {'requestId': 'late'})
            assert name not in callback._pending_tool_response_backlog
        finally:
            callback._current_chat_id.reset(chat_token)
            callback._current_stop_event.reset(event_token)
    asyncio.run(run())
