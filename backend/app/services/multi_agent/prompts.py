"""
多智能体系统 prompt 加载器

每个 agent 从 prompts/{agent_name}/ 目录加载专用 prompt，
同时合并 prompts/common/ 目录的通用规则。
"""

from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


@lru_cache(maxsize=128)
def _read_md(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"prompt 文件不存在: {path}")
    return path.read_text(encoding="utf-8").strip()


def _load_dir(directory: Path) -> list[str]:
    """加载目录下所有 .md 文件，按文件名排序。"""
    if not directory.is_dir():
        return []
    return [_read_md(f) for f in sorted(directory.glob("*.md"))]


def get_agent_prompt(agent_name: str) -> str:
    """
    获取指定 agent 的完整系统 prompt。

    合并顺序：common/*.md → {agent_name}/*.md
    """
    parts: list[str] = []
    parts.extend(_load_dir(_PROMPTS_DIR / "common"))
    parts.extend(_load_dir(_PROMPTS_DIR / f"{agent_name}_agent"))
    if not parts:
        raise ValueError(f"未找到 agent '{agent_name}' 的 prompt 文件")
    return "\n\n".join(parts)
