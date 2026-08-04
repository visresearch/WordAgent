import ast
import inspect
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.api.routes import chat
from app.services.agent import agent as single_agent


class FakeWebSocket:
    def __init__(self, checkpointer=None):
        self.sent: list[str] = []
        self.app = SimpleNamespace(state=SimpleNamespace(checkpointer=checkpointer))

    async def send_text(self, payload: str) -> None:
        self.sent.append(payload)

    async def close(self, **_kwargs) -> None:
        return None


class ContextOverflowRetryTests(unittest.IsolatedAsyncioTestCase):
    def test_insufficient_balance_has_actionable_message(self):
        error = RuntimeError("Error code: 402 - Insufficient Balance")
        message = single_agent._friendly_agent_error_message(error)

        self.assertIn("余额不足", message)
        self.assertIn("切换", message)

    def test_invalid_tool_call_has_actionable_message(self):
        error = RuntimeError("模型连续生成无效工具调用参数: generate_document")
        message = single_agent._friendly_agent_error_message(error)

        self.assertIn("工具参数格式无效", message)
        self.assertIn("拆分", message)

    def test_agent_generators_rethrow_context_overflow_before_generic_errors(self):
        stream_fn = single_agent.process_writing_request_stream
        tree = ast.parse(inspect.getsource(stream_fn))
        matching_handlers = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            handler_names = [
                handler.type.id if isinstance(handler.type, ast.Name) else None for handler in node.handlers
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

    def test_api_uses_single_agent_context_overflow_type(self):
        self.assertIs(chat.ContextOverflowError, single_agent.ContextOverflowError)

    async def test_single_agent_context_overflow_is_not_retried(self):
        websocket = FakeWebSocket(checkpointer=object())
        calls = 0

        async def fake_state_stream(**_kwargs):
            nonlocal calls
            calls += 1
            raise single_agent.ContextOverflowError("context overflow")
            yield  # pragma: no cover

        with patch.object(chat, "_single_agent_stream_with_state", new=fake_state_stream):
            await chat._run_ws_stream(
                websocket=websocket,
                chat_id="test-agent",
                message="continue",
                mode="agent",
                model="test-model",
                provider="test-provider",
                document_range=None,
                document_meta=None,
            )

        payloads = [json.loads(raw) for raw in websocket.sent]
        self.assertEqual(calls, 1)
        self.assertEqual(sum(item.get("type") == "error" for item in payloads), 1)
        self.assertEqual(sum(item.get("type") == "done" for item in payloads), 1)


if __name__ == "__main__":
    unittest.main()
