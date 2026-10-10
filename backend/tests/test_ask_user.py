import asyncio
import json

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Interrupt

from app.api.routes import chat
from app.services.agent import agent
from app.services.human_input import answer_command, load_pending_questions
from app.services.memory import build_thread_config


class Model(FakeMessagesListChatModel):
    seen: list = []
    contexts: list = []

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, **kwargs):
        from app.services.tools.callback import _current_request_context

        self.seen.append(list(messages))
        self.contexts.append(_current_request_context.get())
        return super()._generate(messages, **kwargs)


@pytest.mark.parametrize("question_format", ["legacy", "batch", "mixed"])
def test_production_stream_interrupt_restart_resume_and_tool_memory(tmp_path, monkeypatch, question_format):
    questions = [
        {"question": "采用哪种风格？", "options": ["正式", "轻松"]},
        {"question": "字数要求？", "options": []},
    ]
    answers = ["正式", "大约 800 字，附上小标题"]
    calls = [
        {"name": "ask_user", "args": question, "id": f"ask-{index + 1}"} for index, question in enumerate(questions)
    ]
    expected_results = [("ask-1", answers[0]), ("ask-2", answers[1])]
    if question_format != "legacy":
        calls = [{"name": "ask_user", "args": {"questions": questions.copy()}, "id": "ask-batch"}]
        expected_results = [
            (
                "ask-batch",
                json.dumps(
                    {
                        "answers": [
                            {"question": question["question"], "answer": answer}
                            for question, answer in zip(questions, answers, strict=True)
                        ]
                    },
                    ensure_ascii=False,
                ),
            )
        ]
        if question_format == "mixed":
            questions.append({"question": "读者是谁？", "options": ["同事", "客户"]})
            answers.append("同事")
            calls.append({"name": "ask_user", "args": questions[-1], "id": "ask-legacy"})
            expected_results.append(("ask-legacy", "同事"))
    model = Model(
        responses=[
            AIMessage(
                content="",
                tool_calls=calls,
            ),
            AIMessage(content="按你的要求继续"),
            AIMessage(content="记得上次选择"),
        ]
    )
    monkeypatch.setattr(agent, "resolve_model", lambda *args: "fake-model")
    monkeypatch.setattr(agent, "init_chat_model_with_reasoning", lambda *args, **kwargs: model)

    async def mcp():
        return [], [], []

    monkeypatch.setattr(agent, "load_mcp_tools", mcp)
    monkeypatch.setattr(agent, "build_skills_prompt", lambda: "")
    from app.services import llm_client, memory

    monkeypatch.setattr(memory, "is_long_term_memory_enabled", lambda: False)
    monkeypatch.setattr(llm_client, "get_custom_prompt", lambda: "")

    async def collect(saver, **kwargs):
        document_meta = kwargs.pop("document_meta", {"documentName": "原文档"})
        return [
            chunk
            async for chunk in chat._single_agent_stream_with_state(
                checkpointer=saver,
                session_id="test-hitl",
                chat_id="ws-test",
                message="帮我写一下",
                document_range=None,
                document_meta=document_meta,
                model="fake-model",
                provider="",
                mode="agent",
                attached_files=[],
                **kwargs,
            )
        ]

    async def run():
        path = str(tmp_path / "checkpoint.db")
        async with AsyncSqliteSaver.from_conn_string(path) as saver:
            output = await collect(saver)
            events = [json.loads(chunk[6:]) for chunk in output if chunk.startswith("data: {")]
            question = next(event for event in events if event["type"] == "ask_user")
            assert len(question["questions"]) == len(questions)
            assert len(model.seen) == 1  # No model/tool execution until a human answers.
            _, pending = await load_pending_questions(saver, build_thread_config("test-hitl"))
            assert pending == question
            assert await load_pending_questions(saver, build_thread_config("other")) == ([], None)
            await collect(saver)  # A new normal chat cannot bypass the pending interrupt.
            assert len(model.seen) == 1

        async with AsyncSqliteSaver.from_conn_string(path) as saver:
            _, restored = await load_pending_questions(saver, build_thread_config("test-hitl"))
            assert restored == question
            response = {
                "answers": [
                    {"id": item["id"], "answer": answer}
                    for item, answer in zip(question["questions"], answers, strict=True)
                ]
            }
            with pytest.raises(ValueError, match="请回答所有问题"):
                await collect(saver, user_response={"answers": response["answers"][:-1]})
            output = await collect(saver, user_response=response, document_meta={"documentName": "另一个文档"})
            assert "按你的要求继续" in "".join(output)
            assert model.contexts[-1] == model.contexts[0]
            logs = json.loads(next(chunk.split(":", 1)[1] for chunk in output if chunk.startswith("__tool_json__:")))
            assert [item["output"] for item in logs["calls"] if item["tool"] == "ask_user"] == answers
            assert len(model.seen) == 2
            seen = model.seen[-1]
            assert len([message for message in seen if isinstance(message, HumanMessage)]) == 1
            results = [message for message in seen if isinstance(message, ToolMessage)]
            assert [(message.tool_call_id, message.content) for message in results] == expected_results
            assert await load_pending_questions(saver, build_thread_config("test-hitl")) == ([], None)
            with pytest.raises(ValueError, match="已回答"):
                await collect(saver, user_response=response)

        async with AsyncSqliteSaver.from_conn_string(path) as saver:
            await collect(saver)
            assert any(
                isinstance(message, ToolMessage) and message.content == expected_results[0][1]
                for message in model.seen[-1]
            )
            assert any(isinstance(message, AIMessage) and message.tool_calls for message in model.seen[-1])

    asyncio.run(run())


@pytest.mark.parametrize(
    "response",
    [
        None,
        {},
        {"answers": []},
        {"answers": [{"id": "stale", "answer": "正式"}]},
        {"answers": [{"id": "i:0", "answer": "   "}]},
        {"answers": [{"id": "i:0", "answer": "x" * 4001}]},
    ],
)
def test_reject_invalid_or_stale_answers(response):
    interrupt = Interrupt(
        id="i", value={"action_requests": [{"name": "ask_user", "args": {"question": "风格？", "options": ["正式"]}}]}
    )
    with pytest.raises(ValueError):
        answer_command([interrupt], response)


def test_websocket_saves_question_before_allowing_resume(monkeypatch):
    from types import SimpleNamespace

    sent, saved = [], []
    question = {"type": "ask_user", "questions": [{"id": "i:0", "question": "风格？", "options": ["正式"]}]}
    response = {"answers": [{"id": "i:0", "answer": "正式"}]}

    async def send_text(payload):
        event = json.loads(payload)
        if event["type"] == "done":
            assert saved, "must persist before the UI can submit a new answer"
        sent.append(event)

    async def stream(**kwargs):
        assert kwargs["user_response"] == response
        yield f"data: {json.dumps(question)}\n\n"
        yield "data: [DONE]\n\n"

    async def persist(**kwargs):
        saved.append(kwargs)

    async def usage(**kwargs):
        pass

    monkeypatch.setattr(chat, "_single_agent_stream_with_state", stream)
    monkeypatch.setattr(chat, "_persist_chat_turn", persist)
    monkeypatch.setattr(chat, "record_token_usage", usage)
    monkeypatch.setattr(chat, "_extract_long_term_memory_sync", lambda *args: None)
    websocket = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(checkpointer=object(), memory_tasks=set())), send_text=send_text
    )

    async def run():
        await chat._run_ws_stream(
            websocket, "ws", "正式", "agent", "fake", "", None, None, session_id="session", user_response=response
        )
        await asyncio.gather(*websocket.app.state.memory_tasks)

    asyncio.run(run())
    assert sent == [question, {"type": "done"}]
    assert saved[0]["assistant_content"] == "风格？"
    assert saved[0]["content_parts"] == [{"type": "ask_user", "request": question}]


@pytest.mark.parametrize("options", [[], ["正式", "轻松"], ["正式", "轻松", "学术"], ["正式", "轻松", "学术", "简洁"]])
def test_question_accepts_two_to_four_options_or_free_text(options):
    from app.services.tools.ask_user import AskUserInput

    assert AskUserInput(question="写作风格？", options=options).questions[0].options == options


@pytest.mark.parametrize("options", [["唯一选项"], ["重复", "重复"], ["一", "二", "三", "四", "五"]])
def test_question_rejects_option_counts_outside_limit(options):
    from app.services.tools.ask_user import AskUserInput

    with pytest.raises(ValueError):
        AskUserInput(question="写作风格？", options=options)


def test_legacy_six_option_checkpoint_still_resumes_with_at_most_four_options():
    from app.services.human_input import pending_questions

    interruption = Interrupt(
        id="legacy",
        value={
            "action_requests": [
                {"name": "ask_user", "args": {"question": "风格？", "options": ["一", "二", "三", "四", "五", "六"]}}
            ]
        },
    )
    pending = pending_questions([interruption])
    assert pending["questions"][0]["options"] == ["一", "二", "三", "四"]
    command = answer_command([interruption], {"answers": [{"id": "legacy:0", "answer": "自填另一种风格"}]})
    assert command.resume["legacy"]["decisions"] == [{"type": "respond", "message": "自填另一种风格"}]


def test_batch_schema_exposes_questions_and_validates_each_item():
    from app.services.tools.ask_user import AskUserInput, build_ask_user

    schema = build_ask_user("Ask questions").args_schema.model_json_schema()
    assert schema["required"] == ["questions"]
    assert "question" not in schema["properties"]
    question = {"question": " 风格？ ", "options": ["正式", "轻松"]}
    assert len(AskUserInput(questions=[question] * 4).questions) == 4
    assert AskUserInput(questions=[question]).questions[0].question == "风格？"
    for args in [
        {"questions": []},
        {"questions": [question] * 5},
        {"questions": [question, {"question": " "}]},
        {"questions": [{"question": "风格？", "options": ["仅一个"]}]},
        {"questions": [{"question": "风格？", "options": ["1", "2", "3", "4", "5"]}]},
        {"questions": [question], "question": "混用？"},
    ]:
        with pytest.raises(ValueError):
            AskUserInput.model_validate(args)


def test_batch_answers_keep_question_mapping_across_actions_and_interrupts():
    from app.services.human_input import pending_questions

    interrupts = [
        Interrupt(
            id=key,
            value={
                "action_requests": [
                    {"name": "ask_user", "args": {"questions": [{"question": "风格？"}, {"question": "字数？"}]}},
                    {"name": "ask_user", "args": {"question": "读者？"}},
                ]
            },
        )
        for key in ("a", "b")
    ]
    pending = pending_questions(interrupts)["questions"]
    answers = [{"id": q["id"], "answer": str(index)} for index, q in enumerate(pending)]
    command = answer_command(interrupts, {"answers": list(reversed(answers))})
    for key, offset in (("a", 0), ("b", 3)):
        decisions = command.resume[key]["decisions"]
        assert len(decisions) == 2
        assert json.loads(decisions[0]["message"])["answers"] == [
            {"question": "风格？", "answer": str(offset)},
            {"question": "字数？", "answer": str(offset + 1)},
        ]
        assert decisions[1]["message"] == str(offset + 2)
    for invalid in (answers[:-1], answers[:-1] + [answers[0]], answers[:-1] + [{"id": "stale", "answer": "有效回答"}]):
        with pytest.raises(ValueError):
            answer_command(interrupts, {"answers": invalid})
