"""Close interrupted tool calls before continuing a persisted conversation."""

from __future__ import annotations

import json
import uuid

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, RemoveMessage, ToolMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from app.core.logging import get_logger

logger = get_logger(__name__)


def repair_interrupted_tool_calls(messages: list[BaseMessage]) -> tuple[list[BaseMessage], list[dict]]:
    """Fill missing results only for tool calls preceding a newer user turn.

    A stopped graph may persist an assistant's calls without their results.
    Keep every existing result and mark the missing ones as unconfirmed, rather
    than replaying document mutations or pretending they never executed.
    Calls in the current turn remain pending until their real tool results arrive.
    """
    latest_user_index = next(
        (index for index in range(len(messages) - 1, -1, -1) if isinstance(messages[index], HumanMessage)),
        -1,
    )
    repaired = []
    interrupted = []
    index = 0
    while index < len(messages):
        message = messages[index]
        repaired.append(message)
        index += 1
        if not isinstance(message, AIMessage) or not message.tool_calls or index - 1 >= latest_user_index:
            continue

        answered = set()
        while index < len(messages) and isinstance(messages[index], ToolMessage):
            result = messages[index]
            answered.add(result.tool_call_id)
            repaired.append(result)
            index += 1
        for call in message.tool_calls:
            call_id = call.get("id")
            if not call_id or call_id in answered:
                continue
            interrupted.append(call)
            repaired.append(
                ToolMessage(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"wordagent:interrupted:{message.id}:{call_id}")),
                    tool_call_id=call_id,
                    name=call.get("name"),
                    status="error",
                    content=json.dumps(
                        {
                            "success": None,
                            "error": "tool_interrupted",
                            "requiresRead": True,
                            "message": (
                                "This tool call was interrupted before its result was recorded. "
                                "It may have already executed in the frontend; its outcome is unconfirmed. "
                                "Read the current document/file state before deciding whether to retry a mutation."
                            ),
                        },
                        ensure_ascii=False,
                    ),
                )
            )
            answered.add(call_id)
    return repaired, interrupted


class ToolHistoryMiddleware(AgentMiddleware):
    """Persist valid tool-call/result ordering before summarization and model use."""

    def before_model(self, state, runtime):
        repaired, interrupted = repair_interrupted_tool_calls(state["messages"])
        if not interrupted:
            return None
        logger.warning(
            "[ToolHistory] 补齐中断工具的未确认记录: count=%s tools=%s",
            len(interrupted),
            [call.get("name") for call in interrupted],
        )
        return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *repaired]}

    async def abefore_model(self, state, runtime):
        return self.before_model(state, runtime)


TOOL_HISTORY_MIDDLEWARE = ToolHistoryMiddleware()
