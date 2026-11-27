"""Add page images to the model request without storing image bytes in chat history."""

import asyncio
from pathlib import Path

from langchain.agents.middleware import AgentMiddleware, ModelRequest
from langchain_core.messages import HumanMessage, ToolMessage

from app.services.document_view import document_view_image_block


def _with_document_views(request: ModelRequest) -> ModelRequest:
    results = []
    for message in reversed(request.messages):
        if not isinstance(message, ToolMessage):
            break
        if message.name == "view_document" and isinstance(message.artifact, dict):
            results.append(message.artifact)
    if not results:
        return request

    profile = request.model.profile or {}
    if profile.get("image_inputs") is False:
        notice = HumanMessage(content="This model does not accept images. The rendered page PNG paths are in the tool result.")
        return request.override(messages=[*request.messages, notice])

    # Some providers only allow text in tool messages. Images use the user
    # role after the complete tool-result group, with paths beside each image.
    content = [{"type": "text", "text": "Rendered document pages from view_document. Inspect the attached page images."}]
    for artifact in reversed(results):
        for label, saved_path in artifact.get("images", []):
            try:
                image = document_view_image_block(Path(saved_path))
            except (OSError, ValueError):
                content.append({"type": "text", "text": f"{label}: image unavailable at {saved_path}."})
            else:
                content.extend([{"type": "text", "text": f"{label}. Saved PNG: {saved_path}"}, image])
    return request.override(messages=[*request.messages, HumanMessage(content=content)])


class DocumentViewMiddleware(AgentMiddleware):
    def wrap_model_call(self, request: ModelRequest, handler):
        return handler(_with_document_views(request))

    async def awrap_model_call(self, request: ModelRequest, handler):
        updated = await asyncio.to_thread(_with_document_views, request)
        return await handler(updated)
