"""Executed with a plugin's own Python interpreter, never in the backend process."""

import json
import sys
from importlib.metadata import entry_points


def main():
    plugins = [entry.load() for entry in entry_points(group="wordagent.plugins")]
    if not plugins:
        raise RuntimeError("Package has no wordagent.plugins entry point")
    if sys.argv[1:] == ["--inspect"]:
        plugin = plugins[0]
        print(
            "PLUGIN_RESULT:"
            + json.dumps(
                {
                    "name": str(plugin.name),
                    "description": str(plugin.description),
                    "capabilities": list(plugin.capabilities),
                },
                ensure_ascii=False,
            )
        )
        return
    if sys.argv[1:] == ["--check"]:
        for plugin in plugins:
            if hasattr(plugin, "check"):
                plugin.check()
        print("PLUGIN_RESULT:" + json.dumps({"ready": True}))
        return
    if len(sys.argv) != 3:
        raise SystemExit("usage: runner.py CAPABILITY JSON_PAYLOAD")
    capability = sys.argv[1]
    payload = json.loads(sys.argv[2])
    for plugin in plugins:
        if capability in plugin.capabilities:
            result = plugin.run(capability, payload)
            print("PLUGIN_RESULT:" + json.dumps(result, ensure_ascii=False))
            return
    raise RuntimeError(f"No plugin provides capability: {capability}")


if __name__ == "__main__":
    main()
