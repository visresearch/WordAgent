"""Prevent inline image bytes from reaching models or remaining in checkpoints."""

import asyncio

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from app.services.image_storage import persist_inline_images


class ImagePathMiddleware(AgentMiddleware):
    def before_model(self, state, runtime):
        messages = []
        changed = False
        for message in state["messages"]:
            updates = {}
            for field in ("content", "additional_kwargs", "tool_calls", "artifact"):
                original = getattr(message, field, None)
                converted = persist_inline_images(original)
                if converted != original:
                    updates[field] = converted
            messages.append(message.model_copy(update=updates) if updates else message)
            changed = changed or bool(updates)
        if changed:
            return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *messages]}
        return None

    async def abefore_model(self, state, runtime):
        return await asyncio.to_thread(self.before_model, state, runtime)
