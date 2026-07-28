import asyncio
import unittest

from app.services.tools.callback import (
    cleanup_tool_request,
    create_tool_request,
    submit_tool_response,
    wait_for_tool_response,
)


class ToolResponseCorrelationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.chat_id = "correlation-test"
        create_tool_request(self.chat_id)

    async def asyncTearDown(self):
        cleanup_tool_request(self.chat_id)

    async def test_routes_out_of_order_responses_by_request_id(self):
        first = asyncio.create_task(wait_for_tool_response(self.chat_id, "req-1", timeout=1))
        second = asyncio.create_task(wait_for_tool_response(self.chat_id, "req-2", timeout=1))
        await asyncio.sleep(0)

        await submit_tool_response(
            self.chat_id,
            {"type": "insert_break_response", "requestId": "req-2", "success": True},
        )
        await submit_tool_response(
            self.chat_id,
            {"type": "generate_document_response", "requestId": "req-1", "success": True},
        )

        self.assertEqual((await first)["requestId"], "req-1")
        self.assertEqual((await second)["requestId"], "req-2")

    async def test_keeps_early_response_until_waiter_is_registered(self):
        payload = {
            "type": "generate_document_response",
            "requestId": "early",
            "success": True,
        }
        await submit_tool_response(self.chat_id, payload)
        self.assertEqual(
            await wait_for_tool_response(self.chat_id, "early", timeout=1),
            payload,
        )


if __name__ == "__main__":
    unittest.main()
