import pytest

from app.services.plugins import manager


def test_plugin_install_verify_discover_and_remove(tmp_path, monkeypatch):
    monkeypatch.setenv("WENCE_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(manager, "_uv", lambda: "uv")
    commands = []

    def run(command, log):
        commands.append(command)
        if command[1] == "venv":
            python = manager._python("ocr")
            python.parent.mkdir(parents=True)
            python.touch()
        if command[-1] == "--inspect":
            return 'PLUGIN_RESULT:{"name":"OCR","description":"image text","capabilities":["ocr"]}'
        if command[-1] == "--check":
            assert not manager.has_capability("ocr")
            return 'PLUGIN_RESULT:{"ready":true}'
        return ""

    monkeypatch.setattr(manager, "_run", run)
    info = manager.install_plugin("ocr", lambda _: None)
    assert info["capabilities"] == ["ocr"]
    assert manager.has_capability("ocr")
    assert manager.discover_plugins()[0]["installed"] is True
    assert any(command[-1] == "--check" for command in commands)
    manager.remove_plugin("ocr", lambda _: None)
    assert not manager.has_capability("ocr")
    assert not manager.plugins_dir().joinpath("ocr").exists()


@pytest.mark.parametrize("source", ["../../bad", "evil-plugin", "wordagent-plugin-x;whoami", "https://example.com/x"])
def test_custom_plugin_source_requires_package_name(source):
    with pytest.raises(ValueError):
        manager._parse_source(source)
