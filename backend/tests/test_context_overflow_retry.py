import ast
import asyncio
import inspect
import json
import unittest
from unittest.mock import patch

from app.api.routes import chat
from app.services.agent import agent as single_agent
from app.services.multi_agent import agent as multi_agent


class FakeWebSocket:
    def __init__(self):
        self.sent: list[str] = []

    async def send_text(self, payload: str) -> None:
        self.sent.append(payload)

    async def close(self, **_kwargs) -> None:
        return None


class ContextOverflowRetryTests(unittest.IsolatedAsyncioTestCase):
    def test_agent_generators_rethrow_context_overflow_before_generic_errors(self):
        for stream_fn in (
            single_agent.process_writing_request_stream,
            multi_agent.process_writing_request_stream,
        ):
            with self.subTest(module=stream_fn.__module__):
                tree = ast.parse(inspect.getsource(stream_fn))
                matching_handlers = []
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Try):
                        continue
                    handler_names = [
                        handler.type.id if isinstance(handler.type, ast.Name) else None
                        for handler in node.handlers
                    ]
                    if "ContextOverflowError" in handler_names and "Exception" in handler_names:
                        matching_handlers.append((node, handler_names))

                self.assertTrue(matching_handlers)
                try_node, handler_names = matching_handlers[-1]
                self.assertLess(
                    handler_names.index("ContextOverflowError"),
                    handler_names.index("Exception"),
                )
                overflow_handler = try_node.handlers[handler_names.index("ContextOverflowError")]
                self.assertEqual(len(overflow_handler.body), 1)
                self.assertIsInstance(overflow_handler.body[0], ast.Raise)

    def test_multi_agent_uses_the_api_catchable_exception_type(self):
        self.assertIs(multi_agent.ContextOverflowError, single_agent.ContextOverflowError)
        self.assertIs(chat.ContextOverflowError, single_agent.ContextOverflowError)

    async def test_api_retries_once_without_emitting_generic_error(self):
        for mode, stream_attribute in (("agent", "single_agent_stream"), ("plan", "multi_agent_stream")):
            with self.subTest(mode=mode):
                websocket = FakeWebSocket()
                received_histories: list[list[dict]] = []
                compressed_history = [{"role": "system", "content": "durable task state"}]

                def fake_stream(**kwargs):
                    received_histories.append(kwargs["history"])

                    async def generate():
                        if len(received_histories) == 1:
                            raise single_agent.ContextOverflowError("context overflow", compressed_history)
                        yield 'data: {"type":"text","content":"retry succeeded"}\n\n'
                        yield "data: [DONE]\n\n"

                    return generate()

                async def persist_with_scheduling_point(**_kwargs):
                    await asyncio.sleep(0)

                with (
                    patch.object(chat, stream_attribute, new=fake_stream),
                    patch.object(chat, "_load_short_term_history_from_db", return_value=[]),
                    patch.object(chat, "_persist_chat_turn", new=persist_with_scheduling_point),
                ):
                    await chat._run_ws_stream(
                        websocket=websocket,
                        chat_id=f"test-{mode}",
                        message="continue",
                        mode=mode,
                        model="test-model",
                        provider="test-provider",
                        document_range=None,
                        document_meta=None,
                    )

                payloads = []
                for raw in websocket.sent:
                    try:
                        payloads.append(json.loads(raw))
                    except json.JSONDecodeError:
                        continue

                self.assertEqual(len(received_histories), 2)
                self.assertEqual(received_histories[1], compressed_history)
                self.assertEqual(sum(item.get("type") == "error" for item in payloads), 0)
                self.assertEqual(sum(item.get("type") == "done" for item in payloads), 1)
                self.assertTrue(
                    any(
                        item.get("type") == "status" and "上下文压缩完成" in item.get("content", "")
                        for item in payloads
                    )
                )
                self.assertTrue(
                    any(item.get("type") == "text" and item.get("content") == "retry succeeded" for item in payloads)
                )


if __name__ == "__main__":
    unittest.main()
