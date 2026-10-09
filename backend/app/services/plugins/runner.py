"""Plugin host entry point executed with each plugin's own Python interpreter."""

import inspect
import json
import sys
from importlib.metadata import entry_points
from pathlib import Path

API_VERSION = 1


def _load_plugins():
    plugins = []
    for entry in entry_points(group="wordagent.plugins"):
        try:
            plugin = entry.load()
            if isinstance(plugin, type):
                plugin = plugin()
        except Exception as exc:
            raise RuntimeError(f"Cannot load WordAgent plugin {entry.name}: {exc}") from exc
        version = getattr(plugin, "api_version", API_VERSION)
        if type(version) is not int or version != API_VERSION:
            raise RuntimeError(f"Incompatible plugin API version {version!r}; WordAgent supports version {API_VERSION}")
        if not isinstance(getattr(plugin, "name", None), str) or not plugin.name.strip():
            raise RuntimeError("WordAgent plugin must declare a nonempty name")
        if not isinstance(getattr(plugin, "description", None), str):
            raise RuntimeError("WordAgent plugin description must be a string")
        capabilities = getattr(plugin, "capabilities", None)
        if (
            not isinstance(capabilities, (list, tuple))
            or not capabilities
            or any(not isinstance(cap, str) or not cap.strip() for cap in capabilities)
            or len(set(capabilities)) != len(capabilities)
        ):
            raise RuntimeError("WordAgent plugin capabilities must be a nonempty list of unique strings")
        run = getattr(plugin, "run", None)
        if not callable(run) or inspect.iscoroutinefunction(run):
            raise RuntimeError("WordAgent plugin must implement a synchronous run(capability, payload) method")
        try:
            inspect.signature(run).bind("capability", {})
        except (ValueError, TypeError) as exc:
            raise RuntimeError("Incompatible WordAgent plugin run method; expected run(capability, payload)") from exc
        check = getattr(plugin, "check", None)
        if check is not None and (not callable(check) or inspect.iscoroutinefunction(check)):
            raise RuntimeError("WordAgent plugin check must be a synchronous method")
        plugins.append(plugin)
    if not plugins:
        raise RuntimeError("Python package is not a WordAgent plugin: wordagent.plugins entry point is missing")
    return plugins


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--validate-source":
        source = Path(sys.argv[2])
        for path in source.rglob("*.py"):
            if not path.is_file():
                continue
            try:
                compile(path.read_bytes(), str(path), "exec")
            except (SyntaxError, ValueError) as exc:
                raise RuntimeError(f"Python program is incompatible: {path.relative_to(source)}: {exc}") from exc
        print("PLUGIN_RESULT:" + json.dumps({"pythonVersion": ".".join(map(str, sys.version_info[:3]))}))
        return
    plugins = _load_plugins()
    if sys.argv[1:] == ["--inspect"]:
        plugin = plugins[0]
        print(
            "PLUGIN_RESULT:"
            + json.dumps(
                {
                    "name": str(plugin.name),
                    "description": str(plugin.description),
                    "capabilities": list(dict.fromkeys(cap for item in plugins for cap in item.capabilities)),
                    "apiVersion": API_VERSION,
                },
                ensure_ascii=False,
            )
        )
        return
    if sys.argv[1:] == ["--check"]:
        for plugin in plugins:
            if getattr(plugin, "check", None) is not None:
                try:
                    if plugin.check() is False:
                        raise RuntimeError("check() returned False")
                except Exception as exc:
                    raise RuntimeError(f"Plugin {plugin.name} self-check failed: {exc}") from exc
        print("PLUGIN_RESULT:" + json.dumps({"ready": True}))
        return
    if len(sys.argv) != 3:
        raise SystemExit("usage: runner.py CAPABILITY JSON_PAYLOAD")
    capability = sys.argv[1]
    payload = json.loads(sys.argv[2])
    if not isinstance(payload, dict):
        raise RuntimeError("Plugin payload must be a JSON object")
    for plugin in plugins:
        if capability in plugin.capabilities:
            result = plugin.run(capability, payload)
            if not isinstance(result, dict):
                raise RuntimeError("WordAgent plugin run method must return a JSON object")
            print("PLUGIN_RESULT:" + json.dumps(result, ensure_ascii=False))
            return
    raise RuntimeError(f"No plugin provides capability: {capability}")


if __name__ == "__main__":
    main()
