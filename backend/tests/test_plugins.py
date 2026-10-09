import ast
import io
import json
import os
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

from app.services.plugins import manager, runner


def _python_project(root, requirement=">=3.11", program=None):
    root.mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text(
        '[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n'
        '[project]\nname = "demo-plugin"\nversion = "0.1.0"\n'
        f'requires-python = "{requirement}"\n'
        '[project.entry-points."wordagent.plugins"]\ndemo = "demo_plugin:Plugin"\n'
        '[tool.hatch.build.targets.wheel]\npackages = ["demo_plugin"]\n',
        encoding="utf-8",
    )
    package = root / "demo_plugin"
    package.mkdir()
    (package / "__init__.py").write_text(
        program
        or 'class Plugin:\n    name = "Demo"\n    description = "test plugin"\n'
        '    capabilities = ("demo",)\n'
        '    def run(self, capability, payload):\n        return {"text": payload["text"]}\n',
        encoding="utf-8",
    )
    return root


def test_plugin_install_verify_discover_and_remove(tmp_path, monkeypatch):
    monkeypatch.setenv("WENCE_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(manager, "_uv", lambda: "uv")
    downloads = []

    def download(item, log, temp_dir):
        downloads.append(item["source"])
        return _python_project(temp_dir / item["package"])

    monkeypatch.setattr(manager, "_download_plugin_source", download)
    commands = []

    def run(command, log):
        commands.append(command)
        if command[1] == "venv":
            python = manager._python("ocr")
            python.parent.mkdir(parents=True)
            python.touch()
        if command[-1] == "--inspect":
            return 'PLUGIN_RESULT:{"name":"OCR","description":"image text","capabilities":["ocr"]}'
        if "--validate-source" in command:
            return 'PLUGIN_RESULT:{"pythonVersion":"3.11.14"}'
        if command[-1] == "--check":
            assert not manager.has_capability("ocr")
            return 'PLUGIN_RESULT:{"ready":true}'
        return ""

    monkeypatch.setattr(manager, "_run", run)
    info = manager.install_plugin("ocr", lambda _: None)
    assert info["capabilities"] == ["ocr"]
    assert downloads == [manager.CATALOG[0]["source"]]
    assert manager.has_capability("ocr")
    assert manager.discover_plugins()[0]["installed"] is True
    assert any(command[-1] == "--check" for command in commands)
    manager.remove_plugin("ocr", lambda _: None)
    assert not manager.has_capability("ocr")
    assert not manager.plugins_dir().joinpath("ocr").exists()


@pytest.mark.parametrize(
    "source",
    [
        "../../bad",
        "evil-plugin",
        "wordagent-plugin-demo==1.0.0",
        "wordagent-plugin-x;whoami",
        "https://example.com/x",
        "http://github.com/owner/repo",
        "https://github.com/owner",
        "https://github.com/owner/repo/blob/main/plugin.py",
        "https://github.com/owner/repo/tree/main/../bad",
        "https://github.com/owner/repo/tree/main/%2e%2e/bad",
        "https://github.com/owner/repo/tree/main/bad%5cpath",
    ],
)
def test_custom_plugin_source_requires_github_url(source):
    with pytest.raises(ValueError):
        manager._parse_source(source)


def _github_response(request, files):
    url = urlsplit(request.full_url)
    if url.netloc == "api.github.com":
        folder = url.path.split("/contents/", 1)[1]
        ref = parse_qs(url.query).get("ref", ["main"])[0]
        children = {}
        for file_path in files:
            prefix = folder + "/" if folder else ""
            if file_path.startswith(prefix):
                name, *remaining = file_path[len(prefix) :].split("/")
                child_path = prefix + name
                children[name] = {
                    "name": name,
                    "path": child_path,
                    "type": "dir" if remaining else "file",
                    "download_url": None
                    if remaining
                    else f"https://raw.githubusercontent.com/visresearch/WordAgent/{ref}/{child_path}",
                }
        return io.BytesIO(json.dumps(list(children.values())).encode())
    assert url.netloc == "raw.githubusercontent.com"
    file_path = url.path.split("/", 4)[4]
    return io.BytesIO(files[file_path])


def test_catalog_downloads_the_entire_github_folder(tmp_path, monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    folder = "backend/resources/plugins/wordagent-plugin-ocr"
    files = {
        folder + "/pyproject.toml": b"[project]\nname = 'wordagent-plugin-ocr'\n",
        folder + "/README.md": b"plugin readme",
        folder + "/src/wordagent_plugin_ocr/__init__.py": b"",
        folder + "/src/wordagent_plugin_ocr/plugin.py": b"class Plugin: pass\n",
        folder + "/assets/nested/model-config.bin": b"\x00\x01\xff",
    }
    requests = []

    def download(request, timeout):
        requests.append(request.full_url)
        return _github_response(request, files)

    monkeypatch.setattr(manager, "urlopen", download)
    source = manager._download_plugin_source(manager.CATALOG[0], lambda _: None, tmp_path)
    downloaded = {
        path.relative_to(source).as_posix(): path.read_bytes() for path in source.rglob("*") if path.is_file()
    }
    assert downloaded == {name.removeprefix(folder + "/"): value for name, value in files.items()}
    assert all("/backend/resources/plugins/" in url for url in requests)
    assert any("?ref=master" in url for url in requests)


def test_release_source_404_cleans_partial_files_then_falls_back_to_catalog_branch(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "v9.9.9")
    folder = "backend/resources/plugins/wordagent-plugin-ocr"
    requests = []
    files = {folder + "/pyproject.toml": b"[project]\n"}

    def download(request, timeout):
        requests.append(request.full_url)
        url = urlsplit(request.full_url)
        if url.netloc == "api.github.com" and parse_qs(url.query)["ref"][0] == "v9.9.9":
            if url.path.endswith("/missing"):
                raise HTTPError(request.full_url, 404, "Not Found", None, None)
            return io.BytesIO(
                json.dumps(
                    [
                        {
                            "name": "stale.txt",
                            "path": folder + "/stale.txt",
                            "type": "file",
                            "download_url": f"https://raw.githubusercontent.com/visresearch/WordAgent/v9.9.9/{folder}/stale.txt",
                        },
                        {"name": "missing", "path": folder + "/missing", "type": "dir"},
                    ]
                ).encode()
            )
        if url.path.endswith("/stale.txt"):
            return io.BytesIO(b"partial release download")
        return _github_response(request, files)

    monkeypatch.setattr(manager, "urlopen", download)
    source = manager._download_plugin_source(manager.CATALOG[0], lambda _: None, tmp_path)
    assert (source / "pyproject.toml").is_file()
    assert not (source / "stale.txt").exists()
    assert "ref=v9.9.9" in requests[0]
    assert any("ref=master" in request for request in requests)


def test_github_rate_limit_does_not_retry_other_refs(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "v9.9.9")
    requests = []

    def fail(request, timeout):
        requests.append(request.full_url)
        raise HTTPError(request.full_url, 403, "Rate limited", None, None)

    monkeypatch.setattr(manager, "urlopen", fail)
    with pytest.raises(HTTPError) as error:
        manager._download_plugin_source(manager.CATALOG[0], lambda _: None, tmp_path)
    assert error.value.code == 403
    assert len(requests) == 1


def test_unpublished_catalog_folder_has_an_actionable_install_error(tmp_path, monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)

    def fail(request, timeout):
        raise HTTPError(request.full_url, 404, "Not Found", None, None)

    monkeypatch.setattr(manager, "urlopen", fail)
    with pytest.raises(RuntimeError, match="Publish the resources/plugins folder"):
        manager._download_plugin_source(manager.CATALOG[0], lambda _: None, tmp_path)


@pytest.mark.parametrize(
    "entry",
    [
        {"name": "../escape", "type": "file"},
        {"name": "link", "type": "symlink"},
        {"name": "submodule", "type": "file", "submodule_git_url": "https://example.com/repo"},
    ],
)
def test_download_rejects_paths_and_entries_outside_plugin_files(tmp_path, monkeypatch, entry):
    monkeypatch.delenv("APP_VERSION", raising=False)
    folder = "backend/resources/plugins/wordagent-plugin-ocr"
    entry = {**entry, "path": folder + "/" + entry["name"]}
    monkeypatch.setattr(manager, "urlopen", lambda request, timeout: io.BytesIO(json.dumps([entry]).encode()))
    with pytest.raises(ValueError):
        manager._download_plugin_source(manager.CATALOG[0], lambda _: None, tmp_path)
    assert not (tmp_path / "escape").exists()


def test_catalog_supports_new_plugin_ids_without_ocr_specific_code(monkeypatch):
    item = {
        "id": "pdf",
        "package": "wordagent-plugin-pdf",
        "source": "https://github.com/owner/wordagent/tree/main/pdf",
    }
    monkeypatch.setattr(manager, "CATALOG", (item,))
    assert manager._parse_source("pdf") == ("pdf", item["source"])
    assert manager._parse_source("wordagent-plugin-pdf") == ("pdf", item["source"])
    assert manager._parse_source(item["source"] + "/") == ("pdf", item["source"])


def test_install_failure_removes_environment_and_leaves_plugin_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("WENCE_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(manager, "_uv", lambda: "uv")
    monkeypatch.setattr(
        manager, "_download_plugin_source", lambda item, log, temp: _python_project(temp / item["package"])
    )

    def fail(command, log):
        raise RuntimeError("installation failed")

    monkeypatch.setattr(manager, "_run", fail)
    with pytest.raises(RuntimeError, match="installation failed"):
        manager.install_plugin("ocr", lambda _: None)
    assert not manager.has_capability("ocr")
    assert not manager.plugins_dir().joinpath("ocr").exists()


def test_custom_github_ids_are_stable_and_do_not_collide_between_repositories():
    first = manager._parse_source("https://github.com/owner/first/tree/main/plugin")
    assert first == manager._parse_source("https://github.com/OWNER/FIRST/tree/main/plugin/")
    assert first[0] != manager._parse_source("https://github.com/owner/second/tree/main/plugin")[0]
    assert manager._parse_source("https://github.com/owner/repo.git")[1] == "https://github.com/owner/repo"


def test_repository_root_download_uses_default_branch_without_app_release(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "v9.9.9")
    source_url = "https://github.com/owner/demo"
    plugin_id, source_url = manager._parse_source(source_url)
    item = {"id": plugin_id, "package": plugin_id, "source": source_url}
    files = {"pyproject.toml": b"[project]\n", "src/demo.py": b"pass\n"}
    requests = []

    def download(request, timeout):
        requests.append(request.full_url)
        return _github_response(request, files)

    monkeypatch.setattr(manager, "urlopen", download)
    source = manager._download_plugin_source(item, lambda _: None, tmp_path)
    assert (source / "src/demo.py").read_bytes() == b"pass\n"
    assert not any("?ref=" in url for url in requests)


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ("missing-project", "pyproject.toml is missing"),
        ("invalid-toml", "Invalid Python plugin pyproject.toml"),
        ("no-entry", "not a compatible WordAgent plugin"),
        ("invalid-entry", "Invalid WordAgent plugin entry point"),
        ("no-python", "contains no .py"),
        ("invalid-python-requirement", "Invalid plugin Python version requirement"),
    ],
)
def test_invalid_source_fails_before_creating_a_python_environment(tmp_path, monkeypatch, change, error):
    monkeypatch.setenv("WENCE_DATA_DIR", str(tmp_path / "data"))
    source = _python_project(tmp_path / "source")
    pyproject = source / "pyproject.toml"
    if change == "missing-project":
        pyproject.unlink()
    elif change == "invalid-toml":
        pyproject.write_text("[project", encoding="utf-8")
    elif change == "no-entry":
        pyproject.write_text('[project]\nname = "ordinary-project"\n', encoding="utf-8")
    elif change == "invalid-entry":
        pyproject.write_text(pyproject.read_text().replace("demo_plugin:Plugin", "invalid entry"), encoding="utf-8")
    elif change == "no-python":
        (source / "demo_plugin/__init__.py").unlink()
    else:
        pyproject.write_text(pyproject.read_text().replace(">=3.11", "not-a-version"), encoding="utf-8")
    monkeypatch.setattr(manager, "_download_plugin_source", lambda *args: source)
    commands = []
    monkeypatch.setattr(manager, "_run", lambda command, log: commands.append(command))
    with pytest.raises(ValueError, match=error):
        manager.install_plugin("https://github.com/owner/plugin", lambda _: None)
    assert not commands
    assert not list(manager.plugins_dir().iterdir())


def test_incompatible_python_requirement_fails_before_dependency_install(tmp_path, monkeypatch):
    monkeypatch.setenv("WENCE_DATA_DIR", str(tmp_path / "data"))
    source = _python_project(tmp_path / "source", requirement=">=3.12")
    monkeypatch.setattr(manager, "_download_plugin_source", lambda *args: source)
    monkeypatch.setattr(manager, "_uv", lambda: "uv")
    commands = []

    def run(command, log):
        commands.append(command)
        return 'PLUGIN_RESULT:{"pythonVersion":"3.11.14"}'

    monkeypatch.setattr(manager, "_run", run)
    with pytest.raises(ValueError, match="Plugin requires Python >=3.12"):
        manager.install_plugin("https://github.com/owner/plugin", lambda _: None)
    assert not any("pip" in command for command in commands)
    assert not list(manager.plugins_dir().iterdir())


class _CompatiblePlugin:
    name = "Demo"
    description = "test plugin"
    capabilities = ("demo",)

    def run(self, capability, payload):
        return payload


@pytest.mark.parametrize(
    ("attributes", "error"),
    [
        ({"api_version": 2}, "Incompatible plugin API"),
        ({"name": ""}, "nonempty name"),
        ({"description": None}, "description must be a string"),
        ({"capabilities": "demo"}, "nonempty list"),
        ({"capabilities": ("demo", "demo")}, "unique strings"),
        ({"run": None}, "must implement a synchronous"),
        ({"run": lambda self: {}}, "expected run"),
        ({"check": False}, "check must be a synchronous"),
    ],
)
def test_runner_rejects_incompatible_plugin_interfaces(monkeypatch, attributes, error):
    plugin = type("IncompatiblePlugin", (_CompatiblePlugin,), attributes)
    monkeypatch.setattr(runner, "entry_points", lambda **kwargs: [SimpleNamespace(name="demo", load=lambda: plugin)])
    with pytest.raises(RuntimeError, match=error):
        runner._load_plugins()


def test_runner_constructs_instance_plugins_and_validates_api(monkeypatch, capsys):
    monkeypatch.setattr(
        runner, "entry_points", lambda **kwargs: [SimpleNamespace(name="demo", load=lambda: _CompatiblePlugin)]
    )
    monkeypatch.setattr(sys, "argv", ["runner.py", "--inspect"])
    runner.main()
    info = manager._result(capsys.readouterr().out)
    assert info["capabilities"] == ["demo"]
    assert info["apiVersion"] == 1


@pytest.mark.parametrize("returns_false", [True, False])
def test_runner_self_check_can_fail(monkeypatch, returns_false):
    def check(self):
        if returns_false:
            return False
        raise RuntimeError("missing model")

    plugin = type("FailedPlugin", (_CompatiblePlugin,), {"check": check})
    monkeypatch.setattr(runner, "entry_points", lambda **kwargs: [SimpleNamespace(name="demo", load=lambda: plugin)])
    monkeypatch.setattr(sys, "argv", ["runner.py", "--check"])
    with pytest.raises(RuntimeError, match="self-check failed"):
        runner.main()


def test_runner_detects_invalid_python_without_importing_source(tmp_path, monkeypatch):
    (tmp_path / "invalid.py").write_text("class :\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["runner.py", "--validate-source", str(tmp_path)])
    with pytest.raises(RuntimeError, match="Python program is incompatible: invalid.py"):
        runner.main()


@pytest.mark.skipif(not shutil.which("uv"), reason="uv is required to exercise isolated installation")
@pytest.mark.parametrize("compatible", [True, False])
def test_custom_plugin_real_environment_install_invoke_and_cleanup(tmp_path, monkeypatch, compatible):
    monkeypatch.setenv("WENCE_DATA_DIR", str(tmp_path / "data"))
    source = "https://github.com/owner/demo"
    plugin_id, _ = manager._parse_source(source)

    def download(item, log, temp):
        project = _python_project(temp / "project")
        if not compatible:
            module = project / "demo_plugin/__init__.py"
            module.write_text(module.read_text() + "    api_version = 2\n", encoding="utf-8")
        return project

    monkeypatch.setattr(manager, "_download_plugin_source", download)
    logs = []
    if compatible:
        info = manager.install_plugin(source, logs.append)
        assert info["source"] == source
        assert info["package"] == "demo-plugin"
        assert manager.invoke_capability("demo", {"text": "installed in isolation"}) == {
            "text": "installed in isolation"
        }
        manager.remove_plugin(plugin_id, logs.append)
    else:
        with pytest.raises(RuntimeError, match="Incompatible plugin API"):
            manager.install_plugin(source, logs.append)
    assert not manager.installed_plugins()
    assert not manager._plugin_dir(plugin_id).exists()


def test_pyinstaller_collects_catalog_and_host_without_downloadable_plugin_payloads():
    backend = Path(__file__).resolve().parents[1]
    spec = backend.parent / "packaging" / "pyinstaller" / "package.spec"
    tree = ast.parse(spec.read_text(encoding="utf-8"))
    collection = [
        node
        for node in tree.body
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id in {"datas", "app_source"} for target in node.targets)
        )
        or (isinstance(node, ast.For) and isinstance(node.iter, ast.Call) and ast.unparse(node.iter.func) == "os.walk")
    ]
    context = {
        "os": os,
        "backend_dir": str(backend),
        "frontend_dir": str(backend.parent / "frontend"),
        "_data": lambda source, target: (source, target),
    }
    exec(compile(ast.Module(body=collection, type_ignores=[]), str(spec), "exec"), context)
    sources = {Path(source).resolve() for source, target in context["datas"]}
    assert backend / "app/services/agent/plugin.json" in sources
    assert backend / "app/services/plugins/runner.py" in sources
    plugin_root = backend / "resources/plugins"
    assert not any(source == plugin_root or plugin_root in source.parents for source in sources)
    assert not any("wordagent-plugin-" in str(source) for source in sources)
