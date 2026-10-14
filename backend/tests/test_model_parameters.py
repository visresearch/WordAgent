import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from sqlalchemy import create_engine, select

from app.api.routes import settings as settings_api
from app.core.db import _initialize_schema
from app.models.db_models import ModelParameterConfig
from app.models.model_config import ModelParameters
from app.services import llm_client, model_settings


@pytest.fixture
def model_store(tmp_path, monkeypatch):
    settings_file = tmp_path / "user_settings.json"
    engine = create_engine(f"sqlite:///{tmp_path / 'settings.db'}")
    monkeypatch.setattr(model_settings, "engine", engine)
    monkeypatch.setattr(model_settings, "get_user_settings_file", lambda: settings_file)
    monkeypatch.setattr(settings_api, "SETTINGS_FILE", settings_file)
    monkeypatch.setattr(llm_client, "SETTINGS_FILE", settings_file)
    with engine.begin() as connection:
        _initialize_schema(connection)
    yield engine, settings_file
    engine.dispose()


def provider(name="DeepSeek", model_id="deepseek-v4-flash", parameters=None, api_type="openai"):
    model = {"id": model_id, "name": model_id, "enabled": True}
    if parameters is not None:
        model["parameters"] = parameters
    return {
        "name": name,
        "baseUrl": "https://provider.example",
        "apiKey": f"key-{name}",
        "apiType": api_type,
        "enabled": True,
        "models": [model],
    }


async def api_request(method, body=None):
    app = FastAPI()
    app.include_router(settings_api.router, prefix="/api/settings")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        return await client.request(method, "/api/settings", json=body)


def save(providers):
    response = asyncio.run(api_request("POST", {"providers": providers}))
    assert response.status_code == 200, response.text


def test_api_persists_model_parameters_and_conversation_reads_database(model_store):
    engine, path = model_store
    parameters = {"temperature": 1.25, "topP": 0.8, "maxTokens": 4096, "reasoningEffort": "high"}
    save([provider(parameters={**parameters, "contextWindow": 1000000})])
    with engine.connect() as connection:
        row = connection.execute(select(ModelParameterConfig.__table__)).one()
        assert (row.temperature, row.top_p, row.max_tokens, row.reasoning_effort) == (1.25, 0.8, 4096, "high")
    # Reopen the database and corrupt only the obsolete JSON parameter mirror.
    engine.dispose()
    data = json.loads(path.read_text())
    data["providers"][0]["models"][0]["parameters"] = {"temperature": 0.1}
    path.write_text(json.dumps(data))
    response = asyncio.run(api_request("GET"))
    assert response.json()["providers"][0]["models"][0]["parameters"] == parameters
    kwargs = llm_client.get_llm_init_kwargs("deepseek-v4-flash", "DeepSeek")
    assert (kwargs["temperature"], kwargs["top_p"], kwargs["max_tokens"], kwargs["reasoning_effort"]) == (
        1.25,
        0.8,
        4096,
        "high",
    )
    assert kwargs["extra_body"] == {"thinking": {"type": "enabled"}}


def test_defaults_and_zero_values_are_preserved(model_store):
    save([provider(parameters={"temperature": 0, "topP": 0, "maxTokens": None, "reasoningEffort": ""})])
    parameters = asyncio.run(api_request("GET")).json()["providers"][0]["models"][0]["parameters"]
    assert parameters == {"temperature": 0, "topP": 0, "maxTokens": 8192, "reasoningEffort": "medium"}
    kwargs = llm_client.get_llm_init_kwargs("auto")
    assert kwargs["temperature"] == 0 and kwargs["top_p"] == 0
    assert kwargs["max_tokens"] == 8192 and kwargs["reasoning_effort"] == "medium"


def test_memory_switch_persists_without_overwriting_other_settings(model_store):
    _, path = model_store
    save([provider(parameters={"maxTokens": 4096})])
    before = json.loads(path.read_text(encoding="utf-8"))
    before.update(enableLongTermMemory=True, customPrompt="Keep my instructions", proofreadMode="revision")
    path.write_text(json.dumps(before), encoding="utf-8")
    response = asyncio.run(api_request("GET"))
    assert response.json()["enableLongTermMemory"] is True
    assert "proofreadMode" not in response.json()
    for enabled in (False, True):
        response = asyncio.run(api_request("POST", {"enableLongTermMemory": enabled}))
        assert response.status_code == 200, response.text
        saved = json.loads(path.read_text(encoding="utf-8"))
        assert saved["enableLongTermMemory"] is enabled
        assert saved["customPrompt"] == "Keep my instructions"
        assert saved["providers"] == before["providers"]
        assert "proofreadMode" not in saved
        assert asyncio.run(api_request("GET")).json()["enableLongTermMemory"] is enabled


@pytest.mark.parametrize(
    "parameters",
    [
        {"temperature": -0.01},
        {"temperature": 2.01},
        {"temperature": float("inf")},
        {"topP": -0.01},
        {"topP": 1.01},
        {"maxTokens": 0},
        {"maxTokens": 1.5},
        {"maxTokens": True},
        {"reasoningEffort": "invalid"},
    ],
)
def test_invalid_api_parameters_cannot_change_persistence(model_store, parameters):
    save([provider()])
    before = model_settings.load_model_parameters()
    if parameters.get("temperature") == float("inf"):
        # Pydantic model validation also rejects non-finite floats before JSON serialization.
        with pytest.raises(ValueError):
            ModelParameters(**parameters)
    else:
        response = asyncio.run(api_request("POST", {"providers": [provider(parameters=parameters)]}))
        assert response.status_code == 422
    assert model_settings.load_model_parameters() == before


def test_legacy_migration_is_idempotent_and_preserves_custom_values(model_store):
    engine, path = model_store
    path.write_text(
        json.dumps(
            {
                "temperature": 0.75,
                "providers": [
                    provider(parameters={"topP": 0.6, "reasoningEffort": "", "maxTokens": None, "contextWindow": 0})
                ],
            }
        )
    )
    with engine.begin() as connection:
        _initialize_schema(connection)
    assert model_settings.load_model_parameters()[("deepseek", "deepseek-v4-flash")] == {
        "temperature": 0.75,
        "topP": 0.6,
        "maxTokens": 8192,
        "reasoningEffort": "medium",
    }
    save([provider(parameters={"temperature": 1.8, "reasoningEffort": "low"})])
    path.write_text(json.dumps({"providers": [provider(parameters={"temperature": 0.1})]}))
    with engine.begin() as connection:
        _initialize_schema(connection)
    assert model_settings.load_model_parameters()[("deepseek", "deepseek-v4-flash")]["temperature"] == 1.8


def test_provider_selection_isolates_identical_model_ids_and_reads_updates(model_store):
    first = provider("First", parameters={"temperature": 0.1, "maxTokens": 1024, "reasoningEffort": "low"})
    second = provider("Second", parameters={"temperature": 1.7, "maxTokens": 16384, "reasoningEffort": "xhigh"})
    save([first, second])
    kwargs = llm_client.get_llm_init_kwargs("auto", "Second")
    assert (kwargs["api_key"], kwargs["temperature"], kwargs["max_tokens"], kwargs["reasoning_effort"]) == (
        "key-Second",
        1.7,
        16384,
        "xhigh",
    )
    second["models"][0]["parameters"]["reasoningEffort"] = "medium"
    save([first, second])
    assert llm_client.get_llm_init_kwargs("deepseek-v4-flash", "Second")["reasoning_effort"] == "medium"
    with pytest.raises(ValueError, match="未找到模型"):
        llm_client.get_llm_init_kwargs("deepseek-v4-flash", "Missing")


def test_older_clients_and_partial_updates_do_not_reset_model_parameters(model_store):
    parameters = {"temperature": 1.2, "topP": 0.7, "maxTokens": 4096, "reasoningEffort": "high"}
    save([provider(parameters=parameters)])
    save([provider()])
    assert model_settings.load_model_parameters()[("deepseek", "deepseek-v4-flash")] == parameters
    response = asyncio.run(api_request("POST", {"customPrompt": "Keep the settings", "temperature": 0.1}))
    assert response.status_code == 200
    assert model_settings.load_model_parameters()[("deepseek", "deepseek-v4-flash")] == parameters


def test_deleted_models_remove_their_database_rows(model_store):
    save([provider("First"), provider("Second")])
    save([provider("Second")])
    assert set(model_settings.load_model_parameters()) == {("second", "deepseek-v4-flash")}
    save([])
    assert model_settings.load_model_parameters() == {}


def test_unrelated_updates_preserve_database_values_even_if_json_mirror_is_stale(model_store):
    _, path = model_store
    parameters = {"temperature": 1.2, "topP": 0.7, "maxTokens": 4096, "reasoningEffort": "high"}
    save([provider(parameters=parameters)])
    data = json.loads(path.read_text())
    data["providers"][0]["models"][0]["parameters"] = {"temperature": 0.1}
    path.write_text(json.dumps(data))
    response = asyncio.run(api_request("POST", {"customPrompt": "Only change this"}))
    assert response.status_code == 200
    assert model_settings.load_model_parameters()[("deepseek", "deepseek-v4-flash")] == parameters


def test_provider_lookup_normalizes_name_for_auto_model(model_store):
    save([provider("First", model_id="first-model"), provider("Second", model_id="deepseek-v4-flash")])
    assert llm_client.get_llm_init_kwargs("auto", " second ")["model"] == "deepseek-v4-flash"


def test_json_write_failure_rolls_back_database(model_store, monkeypatch):
    save([provider(parameters={"temperature": 0.2})])
    before = model_settings.load_model_parameters()
    monkeypatch.setattr(settings_api, "_write_settings_file", lambda _: (_ for _ in ()).throw(OSError("disk full")))
    response = asyncio.run(api_request("POST", {"providers": [provider(parameters={"temperature": 1.9})]}))
    assert response.status_code == 500
    assert model_settings.load_model_parameters() == before


@pytest.mark.parametrize("effort", ["medium", "high"])
@pytest.mark.parametrize("with_tools", [False, True])
def test_deepseek_request_sends_saved_values_to_wire(model_store, effort, with_tools):
    save([provider(parameters={"temperature": 0.6, "topP": 0.9, "maxTokens": 8192, "reasoningEffort": effort})])
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        chunk = {
            "id": "test",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "deepseek-v4-flash",
            "choices": [{"index": 0, "delta": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
        }
        return httpx.Response(
            200, text=f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n", headers={"content-type": "text/event-stream"}
        )

    kwargs = llm_client.get_llm_init_kwargs("deepseek-v4-flash")
    kwargs.pop("model_provider")
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        model = llm_client.ChatOpenAI(**kwargs, http_client=client)
        if with_tools:
            model = model.bind_tools(
                [{"type": "function", "function": {"name": "read_document", "parameters": {"type": "object"}}}]
            )
        assert model.invoke([HumanMessage(content="hello")]).content == "ok"
    payload = requests[0]
    assert (payload["temperature"], payload["top_p"], payload["reasoning_effort"]) == (0.6, 0.9, effort)
    assert payload.get("max_tokens", payload.get("max_completion_tokens")) == 8192
    assert payload["thinking"] == {"type": "enabled"}
    assert bool(payload.get("tools")) == with_tools


def test_saved_effort_alone_controls_reasoning_without_resetting_other_parameters(model_store):
    save([provider(parameters={"reasoningEffort": "high", "maxTokens": 4096})])
    kwargs = llm_client.get_llm_init_kwargs("deepseek-v4-flash")
    assert kwargs["reasoning_effort"] == "high" and kwargs["extra_body"]["thinking"]["type"] == "enabled"
    assert kwargs["max_tokens"] == 4096
    save([provider(parameters={"reasoningEffort": "none"})])
    kwargs = llm_client.get_llm_init_kwargs("deepseek-v4-flash")
    assert kwargs["reasoning_effort"] == "none" and kwargs["extra_body"]["thinking"]["type"] == "disabled"


@pytest.mark.parametrize("model_id, expected", [("claude-sonnet-4-5", "enabled"), ("claude-opus-4-6", "adaptive")])
def test_anthropic_effort_uses_native_protocol_and_valid_output_budget(model_store, model_id, expected):
    save([provider(model_id=model_id, api_type="anthropic")])
    kwargs = llm_client.get_llm_init_kwargs(model_id)
    assert kwargs["max_tokens"] == 8192
    assert kwargs["thinking"]["type"] == expected
    if expected == "enabled":
        assert kwargs["thinking"]["budget_tokens"] == 4096 < kwargs["max_tokens"]
    else:
        assert kwargs["output_config"] == {"effort": "medium"}
    assert "reasoning_effort" not in kwargs and "temperature" not in kwargs and "top_p" not in kwargs


def test_non_reasoning_openai_models_keep_sampling_without_unsupported_effort(model_store):
    save([provider(model_id="gpt-4o", parameters={"temperature": 1.4, "topP": 0.8})])
    kwargs = llm_client.get_llm_init_kwargs("gpt-4o")
    assert kwargs["temperature"] == 1.4 and kwargs["top_p"] == 0.8
    assert "reasoning_effort" not in kwargs and "extra_body" not in kwargs


def test_openai_reasoning_models_enforce_sampling_compatibility(model_store):
    save([provider(model_id="gpt-5.2")])
    kwargs = llm_client.get_llm_init_kwargs("gpt-5.2")
    assert kwargs["reasoning_effort"] == "medium" and "temperature" not in kwargs and "top_p" not in kwargs
    save([provider(model_id="gpt-5.2", parameters={"reasoningEffort": "none"})])
    kwargs = llm_client.get_llm_init_kwargs("gpt-5.2")
    assert kwargs["reasoning_effort"] == "none" and kwargs["temperature"] == 0.5 and kwargs["top_p"] == 1


@pytest.mark.parametrize("model_id", ["claude-sonnet-4-5", "claude-opus-4-6"])
def test_anthropic_none_explicitly_disables_thinking(model_store, model_id):
    save([provider(model_id=model_id, api_type="anthropic", parameters={"reasoningEffort": "none"})])
    kwargs = llm_client.get_llm_init_kwargs(model_id)
    assert kwargs["thinking"] == {"type": "disabled"}
    client = llm_client.init_chat_model_with_reasoning(model_id)
    assert client.thinking == {"type": "disabled"}
    assert client._wence_reasoning_effort == "none"


@pytest.mark.parametrize("model_id", ["o3", "gpt-5", "gpt-6-astra"])
def test_models_without_none_support_do_not_silently_use_default_reasoning(model_store, model_id):
    save([provider(model_id=model_id, parameters={"reasoningEffort": "none"})])
    with pytest.raises(ValueError, match="不支持 Reasoning Effort=none"):
        llm_client.get_llm_init_kwargs(model_id)


@pytest.mark.parametrize("effort", ["none", "medium", "high"])
@pytest.mark.parametrize("mode", ["ask", "agent"])
def test_chat_uses_saved_effort_and_filters_reasoning_from_stream_and_history(model_store, monkeypatch, effort, mode):
    from app.api.routes import chat
    from app.services import memory
    from app.services.agent import agent

    save([provider(parameters={"reasoningEffort": effort})])
    created_models = []
    stream_inputs = []

    class FakeGraph:
        def stream(self, **kwargs):
            stream_inputs.append(kwargs["input"])
            yield (
                "messages",
                (
                    AIMessageChunk(content="", additional_kwargs={"reasoning_content": "secret-delta"}),
                    {"langgraph_node": "model"},
                ),
            )
            yield (
                "messages",
                (
                    AIMessageChunk(content=[{"type": "reasoning", "text": "secret-structured-chunk"}]),
                    {"langgraph_node": "model"},
                ),
            )
            yield (
                "messages",
                (
                    AIMessage(content=[{"type": "thinking", "thinking": "secret-thinking-block"}]),
                    {"langgraph_node": "model"},
                ),
            )
            yield "custom", {"type": "thinking", "content": "secret-custom"}
            yield (
                "messages",
                (
                    AIMessage(content="<think>secret-tagged</think>Visible answer"),
                    {"langgraph_node": "model"},
                ),
            )

    def create_agent(**kwargs):
        created_models.append(kwargs["model"])
        return FakeGraph()

    async def load_mcp_tools():
        return [], [], []

    monkeypatch.setattr(agent, "create_agent", create_agent)
    monkeypatch.setattr(agent, "build_agent_middleware", lambda **_kwargs: [])
    monkeypatch.setattr(agent, "get_base_tools_for_mode", lambda _mode: [])
    monkeypatch.setattr(agent, "load_mcp_tools", load_mcp_tools)
    monkeypatch.setattr(agent, "build_skills_prompt", lambda: "")
    monkeypatch.setattr(memory, "is_long_term_memory_enabled", lambda: False)
    persistence = AsyncMock()
    monkeypatch.setattr(chat, "_persist_chat_turn", persistence)
    monkeypatch.setattr(chat, "record_token_usage", AsyncMock())
    monkeypatch.setattr(chat, "_extract_long_term_memory_sync", lambda *_args: None)
    app = FastAPI()
    app.include_router(chat.router, prefix="/api/chat")
    app.state.checkpointer = SimpleNamespace(aget_tuple=AsyncMock(return_value=None))
    app.state.memory_tasks = set()
    events = []
    with TestClient(app).websocket_connect("/api/chat/ws") as websocket:
        websocket.send_json(
            {
                "type": "chat",
                "message": "Hello",
                "model": "deepseek-v4-flash",
                "provider": "DeepSeek",
                "mode": mode,
                # Old clients cannot override the stored model setting, in either direction.
                "enableThinking": effort == "none",
            }
        )
        while True:
            event = websocket.receive_json()
            events.append(event)
            if event["type"] == "done":
                break
    assert not any(event["type"] == "error" for event in events), events
    assert created_models[0].reasoning_effort == effort
    assert created_models[0]._wence_reasoning_effort == effort
    assert "enable_thinking" not in stream_inputs[0]["request_context"]
    assert any(event.get("content") == "Visible answer" for event in events)
    thought_events = [event for event in events if event["type"] == "thinking"]
    saved = persistence.call_args.kwargs
    assert saved["assistant_content"] == "Visible answer"
    if effort == "none":
        assert not thought_events
        assert "secret-" not in json.dumps(events)
        assert saved["thinking"] is None
        assert "secret-" not in json.dumps(saved["content_parts"])
    else:
        assert thought_events
        assert "secret-delta" in saved["thinking"]
