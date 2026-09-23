import asyncio
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.services import llm_client, memory
from app.services.agent import agent, prompts


@pytest.fixture
def runtime(monkeypatch):
    state = SimpleNamespace(
        custom_prompt="用中文回答我的问题",
        memory="Prefer concise writing.",
        now=datetime(2026, 9, 16, 12, 46, tzinfo=timezone(timedelta(hours=8))),
        reject_images=False,
        inputs=[],
        systems=[],
        middleware_systems=[],
    )

    class FakeGraph:
        def stream(self, **kwargs):
            messages = kwargs["input"]["messages"]
            state.inputs.append(messages)
            if state.reject_images and isinstance(messages[-1].content, list):
                raise RuntimeError("does not support image input")
            yield "messages", (AIMessage(content="完成"), {"langgraph_node": "model"})

    def create_agent(**kwargs):
        state.systems.append(kwargs["system_prompt"])
        return FakeGraph()

    def middleware(**kwargs):
        state.middleware_systems.append(kwargs["system_prompt"])
        return []

    async def load_mcp_tools():
        return [], [], []

    monkeypatch.setattr(agent, "resolve_model", lambda *_args: "fake-model")
    monkeypatch.setattr(agent, "supports_thinking", lambda _model: False)
    monkeypatch.setattr(agent, "init_chat_model_with_reasoning", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(agent, "load_mcp_tools", load_mcp_tools)
    monkeypatch.setattr(agent, "get_base_tools_for_mode", lambda _mode: [])
    monkeypatch.setattr(agent, "build_mcp_tools_prompt", lambda _tools: "Fixed MCP description")
    monkeypatch.setattr(agent, "build_skills_prompt", lambda: "Fixed skills description")
    monkeypatch.setattr(agent, "build_agent_middleware", middleware)
    monkeypatch.setattr(agent, "create_agent", create_agent)
    monkeypatch.setattr(agent, "datetime", SimpleNamespace(now=lambda: state.now))
    monkeypatch.setattr(agent, "_langsmith_enabled", False)
    monkeypatch.setattr(llm_client, "get_custom_prompt", lambda: state.custom_prompt)
    monkeypatch.setattr(memory, "is_long_term_memory_enabled", lambda: bool(state.memory))
    monkeypatch.setattr(memory, "build_long_term_memory_prompt", lambda: state.memory)
    return state


def collect(**kwargs):
    async def run():
        return [chunk async for chunk in agent.process_writing_request_stream(model="fake", **kwargs)]

    result = asyncio.run(run())
    assert not any('"type": "error"' in item for item in result)
    return result


@pytest.mark.parametrize("mode", ["agent", "ask"])
def test_system_stays_identical_when_preferences_time_and_memory_change(runtime, mode):
    collect(message="第一次请求", mode=mode)
    first_user = runtime.inputs[0][-1]
    assert isinstance(first_user, HumanMessage)
    assert runtime.custom_prompt in first_user.content
    assert runtime.memory in first_user.content
    assert "Current time:" in first_user.content
    assert first_user.content.endswith("[User Request]\n第一次请求")

    runtime.custom_prompt = "Please answer in English."
    runtime.memory = "New remembered preference."
    runtime.now += timedelta(days=1, hours=2)
    collect(message="第二次请求", mode=mode)
    second_user = runtime.inputs[1][-1].content

    assert runtime.systems[0] == runtime.systems[1]
    assert runtime.systems == runtime.middleware_systems
    assert "Fixed MCP description" in runtime.systems[0]
    assert "Fixed skills description" in runtime.systems[0]
    for dynamic_text in (
        "用中文回答",
        "Please answer in English.",
        "Current time:",
        "Prefer concise",
        "New remembered",
    ):
        assert dynamic_text not in runtime.systems[0]
    assert runtime.custom_prompt in second_user
    assert runtime.memory in second_user
    assert "用中文回答" not in second_user
    assert first_user.content != second_user


def test_user_prompt_has_explicit_sections_timezone_and_unmodified_request():
    message = "  保留原始文本\n包括空行\n\n和结尾空格  "
    result = prompts.build_user_prompt(
        message,
        custom_prompt="使用中文",
        request_time=datetime(2026, 9, 16, 12, 46, tzinfo=timezone(timedelta(hours=8))),
        long_term_memory="旧偏好",
        context_sections=["[Selected Document Ranges]\ndocId=7", "[Attached Files]\nuploads/a.txt"],
    )
    assert "Current time: 2026-09-16 12:46 Wednesday (UTC+08:00)" in result
    headings = [
        "[User Custom Instructions]",
        "[Request Context]",
        "[Long-term Memory]",
        "[Selected Document Ranges]",
        "[Attached Files]",
        "[User Request]",
    ]
    positions = [result.index(heading) for heading in headings]
    assert positions == sorted(positions)
    assert result.endswith("[User Request]\n" + message)


def test_empty_optional_context_is_omitted(runtime):
    runtime.custom_prompt = " \n "
    runtime.memory = ""
    collect(message="你好")
    content = runtime.inputs[0][-1].content
    assert "[User Custom Instructions]" not in content
    assert "[Long-term Memory]" not in content
    assert "[Attached Files]" not in content
    assert content.endswith("[User Request]\n你好")


@pytest.mark.parametrize("mode", ["agent", "ask"])
def test_document_context_and_attachment_references_are_preserved(runtime, mode):
    output = collect(
        message="整理这段内容",
        mode=mode,
        document_range=[{"docId": 7, "startParaIndex": 2, "endParaIndex": 4, "startParaID": 20, "endParaID": 40}],
        document_meta=[
            {"documentId": 7, "documentName": "当前文档", "isEmpty": True},
            {"documentId": 8, "documentName": "参考文档"},
        ],
        attached_files=[{"file_id": "a", "filename": "notes.txt", "project_path": "uploads/a.txt"}],
    )
    content = runtime.inputs[0][-1].content
    assert "《当前文档》docId=7" in content
    assert "selected paraID 20 to 40" in content
    assert content.index('"documentId":7') < content.index('"documentId":8')
    assert '"isEmpty":true' in content
    assert "insertParaID=0" in content
    assert "project_path=uploads/a.txt" in content
    assert "[Attached Files]" in content
    assert content.endswith("[User Request]\n整理这段内容")
    if mode == "ask":
        assert "Please answer based on the above content." in content
    memory_event = next(item for item in output if item.startswith("__memory_conversation__:"))
    conversation = json.loads(memory_event.split(":", 1)[1])
    assert "整理这段内容" in conversation["user"]
    assert "docId=7" in conversation["user"]
    assert "Current time:" not in conversation["user"]
    assert runtime.memory not in conversation["user"]


def test_image_fallback_retains_runtime_context_and_message_identity(runtime, monkeypatch):
    from app.api.routes import files

    monkeypatch.setattr(files, "read_file_as_base64", lambda _file_id: "aW1hZ2U=")
    runtime.reject_images = True
    collect(
        message="分析图片",
        attached_files=[
            {
                "file_id": "image",
                "filename": "image.png",
                "is_image": True,
                "content_type": "image/png",
                "size": 5,
                "project_path": "uploads/image",
            }
        ],
    )
    assert len(runtime.inputs) == 2
    original = runtime.inputs[0][-1]
    fallback = runtime.inputs[1][-1]
    assert original.id == fallback.id
    assert original.content[1]["type"] == "image_url"
    original_text = original.content[0]["text"]
    assert isinstance(fallback.content, str)
    for content in (original_text, fallback.content):
        assert content.count("Current time:") == 1
        assert runtime.custom_prompt in content
        assert runtime.memory in content
        assert "project_path=uploads/image" in content
        assert content.endswith("[User Request]\n分析图片")
    assert "provided as direct model image inputs" in original_text
    assert "Direct image input is unavailable" in fallback.content
    assert "read_file(path)" in fallback.content
    assert original_text.split("[Image Input]")[0] == fallback.content.split("[Image Input]")[0]


def test_image_fallback_includes_downloaded_ocr_text(runtime, monkeypatch):
    from app.api.routes import files

    monkeypatch.setattr(files, "read_file_as_base64", lambda _file_id: "aW1hZ2U=")
    monkeypatch.setattr(
        agent, "_ocr_attachment_context", lambda paths: f"[OCR text from attached images]\n{paths[0]}: 发票金额 120 元"
    )
    runtime.reject_images = True
    collect(
        message="读取这张图片",
        attached_files=[
            {
                "file_id": "image",
                "filename": "receipt.png",
                "is_image": True,
                "content_type": "image/png",
                "size": 5,
                "project_path": "uploads/receipt.png",
            }
        ],
    )
    fallback = runtime.inputs[1][-1]
    assert isinstance(fallback.content, str)
    assert "uploads/receipt.png: 发票金额 120 元" in fallback.content
    assert runtime.inputs[0][-1].id == fallback.id
