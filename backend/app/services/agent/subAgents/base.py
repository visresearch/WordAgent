"""
子智能体基类模块

定义所有子智能体的通用接口。
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseSubAgent(ABC):
    """子智能体基类。"""

    agent_type: str = "base"
    config: dict[str, Any] = {}

    @abstractmethod
    def get_system_prompt(self, context: dict[str, Any] | None = None) -> str:
        """获取系统提示词。"""
        pass

    @abstractmethod
    def get_allowed_tools(self) -> list[str]:
        """获取允许的工具名称列表。"""
        pass


# 全局工具注册表
_TOOL_REGISTRY: dict[str, Any] = {}


def register_tool(tool: Any) -> None:
    """注册工具。"""
    name = getattr(tool, "name", None) or str(tool)
    _TOOL_REGISTRY[name] = tool


def get_tool(name: str) -> Any | None:
    """获取工具。"""
    return _TOOL_REGISTRY.get(name)


def get_all_tools() -> dict[str, Any]:
    """获取所有工具。"""
    return _TOOL_REGISTRY.copy()


def initialize_tool_registry() -> None:
    """初始化工具注册表。"""
    if _TOOL_REGISTRY:
        return

    from app.services.agent.tools.document_tools import (
        delete_document,
        generate_document,
        read_document,
        search_documnet,
    )

    for tool in [read_document, search_documnet, generate_document, delete_document]:
        register_tool(tool)
