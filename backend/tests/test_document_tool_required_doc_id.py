import pytest
from pydantic import ValidationError

from app.services.agent.tools import read_document, search_document


@pytest.mark.parametrize(
    ("document_tool", "other_required_args"),
    [
        (read_document, {}),
        (search_document, {"query": {"filters": {"regex": "目标文本"}}}),
    ],
)
def test_document_lookup_tools_require_doc_id(document_tool, other_required_args) -> None:
    schema = document_tool.args_schema.model_json_schema()

    assert "docId" in schema["required"]
    with pytest.raises(ValidationError):
        document_tool.args_schema.model_validate(other_required_args)


@pytest.mark.parametrize(
    ("document_tool", "other_required_args"),
    [
        (read_document, {}),
        (search_document, {"query": {"filters": {"regex": "目标文本"}}}),
    ],
)
def test_document_lookup_tools_reject_null_doc_id(document_tool, other_required_args) -> None:
    with pytest.raises(ValidationError):
        document_tool.args_schema.model_validate({**other_required_args, "docId": None})
