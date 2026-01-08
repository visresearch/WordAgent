"""
工具函数
"""

import json
from typing import Any


def pretty_print(data: Any, title: str = "") -> None:
    """格式化打印数据"""
    print("=" * 50)
    if title:
        print(f"[{title}]")
    if isinstance(data, (dict, list)):
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(data)
    print("=" * 50)
