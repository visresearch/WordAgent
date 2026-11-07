import ast
import builtins
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import tomllib

from app.services.plugins import manager
from app.services.tools import file_tools

BACKEND = Path(__file__).resolve().parents[1]
PLUGIN_SOURCE = BACKEND / "resources/plugins/wordagent-plugin-pdf"


@pytest.fixture
def pdf_plugin():
    spec = importlib.util.spec_from_file_location("pdf_plugin_test", PLUGIN_SOURCE / "src/wordagent_plugin_pdf/plugin.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Plugin


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("WENCE_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(file_tools, "get_stream_writer", lambda: None)
    root = tmp_path / "project"
    (root / "uploads").mkdir(parents=True)
    (root / "uploads/report.pdf").write_bytes(b"%PDF-test")
    (root / "uploads/notes.txt").write_text("Plain text still works", encoding="utf-8")
    return root


def test_pdf_plugin_is_optional_in_catalog_dependencies_and_bundle(monkeypatch):
    monkeypatch.setattr(manager, "installed_plugins", lambda: [])
    project = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((BACKEND / "uv.lock").read_text(encoding="utf-8"))
    assert not any("pymupdf" in dependency.lower() for dependency in project["project"]["dependencies"])
    assert not any(package["name"].startswith("pymupdf") for package in lock["package"])
    item = next(item for item in manager.discover_plugins() if item["id"] == "wordagent-plugin-pdf")
    assert item["installed"] is False
    assert item["capabilities"] == ["pdf"]
    assert item["source"].endswith("/backend/resources/plugins/wordagent-plugin-pdf")
    metadata = manager._validate_plugin_source(PLUGIN_SOURCE, lambda _: None)
    assert metadata["entry-points"]["wordagent.plugins"]["pdf"] == "wordagent_plugin_pdf.plugin:Plugin"
    assert any(dependency.startswith("pymupdf") for dependency in metadata["dependencies"])

    spec = ast.parse((BACKEND.parent / "packaging/pyinstaller/package.spec").read_text(encoding="utf-8"))
    analysis = next(node for node in ast.walk(spec) if isinstance(node, ast.Call) and ast.unparse(node.func) == "Analysis")
    exclusions = ast.literal_eval(next(keyword.value for keyword in analysis.keywords if keyword.arg == "excludes"))
    assert {"wordagent_plugin_pdf", "pymupdf", "fitz", "pymupdf4llm", "pymupdf_layout"} <= set(exclusions)


def test_reading_pdf_without_plugin_prompts_installation_and_keeps_other_files_available(project, monkeypatch):
    original_import = builtins.__import__

    def no_pdf_import(name, *args, **kwargs):
        assert name not in {"fitz", "pymupdf"}, "The backend must not import the optional PDF library"
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_pdf_import)
    monkeypatch.setattr(manager.subprocess, "run", lambda *args, **kwargs: pytest.fail("No plugin should run"))
    reader = file_tools.build_read_file("Read a project file")
    result = reader.invoke({"path": "uploads/report.pdf"})
    assert result.startswith("[PDF] uploads/report.pdf\n")
    assert "pdf is not installed" in result
    assert "Settings > Plugins" in result
    assert "Plain text still works" in reader.invoke({"path": "uploads/notes.txt"})
    assert not manager.plugins_dir().exists()


def test_reading_pdf_invokes_isolated_plugin_and_uninstall_restores_installation_prompt(project, monkeypatch):
    plugin_id = "wordagent-plugin-pdf"
    python = manager._python(plugin_id)
    python.parent.mkdir(parents=True)
    python.touch()
    (manager._plugin_dir(plugin_id) / "plugin.json").write_text(json.dumps({
        "id": plugin_id, "capabilities": ["pdf"]
    }), encoding="utf-8")
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        assert command[:3] == [str(python), str(manager._runner()), "pdf"]
        assert json.loads(command[3]) == {"path": str(project / "uploads/report.pdf")}
        return SimpleNamespace(returncode=0, stdout='PLUGIN_RESULT:{"text":"First page\\nSecond page"}', stderr="")

    monkeypatch.setattr(manager.subprocess, "run", run)
    reader = file_tools.build_read_file("Read a project file")
    assert reader.invoke({"path": "uploads/report.pdf", "start_line": 2, "end_line": 2}) == (
        "[PDF] uploads/report.pdf\n2|Second page"
    )
    manager.remove_plugin(plugin_id, lambda _: None)
    assert "pdf is not installed" in reader.invoke({"path": "uploads/report.pdf"})
    assert len(commands) == 1


@pytest.mark.parametrize("text", ["", "A" * 90_000])
def test_pdf_read_preserves_empty_text_handling_and_output_limit(project, monkeypatch, text):
    monkeypatch.setattr(manager, "invoke_capability", lambda capability, payload: {"text": text})
    reader = file_tools.build_read_file("Read a project file")
    result = reader.invoke({"path": "uploads/report.pdf"})
    if not text:
        assert "PDF extracted no readable text" in result
    else:
        assert "truncated" in result
        assert len(result) < 81_000


def test_pdf_plugin_failure_returns_a_read_error(project, monkeypatch):
    def fail(capability, payload):
        raise RuntimeError("Cannot open encrypted PDF")

    monkeypatch.setattr(manager, "invoke_capability", fail)
    result = file_tools.build_read_file("Read a project file").invoke({"path": "uploads/report.pdf"})
    assert "PDF text extraction failed: Cannot open encrypted PDF" in result


class Document:
    def __init__(self, pages):
        self.pages = [SimpleNamespace(get_text=lambda text=text: text) for text in pages]
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def __iter__(self):
        return iter(self.pages)


@pytest.mark.parametrize(("pages", "expected"), [(["First page\n", "Second page\n"], "First page\n\nSecond page"), (["\n", ""], "")])
def test_pdf_plugin_extracts_pages_in_order_and_closes_document(pdf_plugin, monkeypatch, pages, expected):
    document = Document(pages)
    monkeypatch.setitem(sys.modules, "pymupdf", SimpleNamespace(open=lambda path: document))
    assert pdf_plugin.run("pdf", {"path": "report.pdf"}) == {"text": expected}
    assert document.closed


def test_pdf_plugin_closes_document_on_extraction_failure(pdf_plugin, monkeypatch):
    def fail():
        raise RuntimeError("Broken PDF page")

    document = Document([""])
    document.pages[0].get_text = fail
    monkeypatch.setitem(sys.modules, "pymupdf", SimpleNamespace(open=lambda path: document))
    with pytest.raises(RuntimeError, match="Broken PDF page"):
        pdf_plugin.run("pdf", {"path": "report.pdf"})
    assert document.closed


def test_pdf_plugin_rejects_unrelated_capabilities(pdf_plugin):
    with pytest.raises(ValueError, match="Unsupported capability: ocr"):
        pdf_plugin.run("ocr", {})
