# """Skills 与命令执行工具。"""

# from dataclasses import dataclass
# from pathlib import Path
# import re
# import subprocess

# from langchain_core.tools import tool
# from langgraph.config import get_stream_writer

# from app.core.config import get_wence_data_dir


# @dataclass
# class SkillMetadata:
#     """Skill 元数据。"""

#     name: str
#     description: str
#     skill_path: Path
#     skill_md_path: Path


# DEFAULT_SKILL_PATHS = [
#     get_wence_data_dir() / ".claude" / "skills",
#     Path.cwd() / ".claude" / "skills",
#     Path.home() / ".claude" / "skills",
# ]


# def _extract_frontmatter(content: str) -> tuple[dict[str, str], str]:
#     """提取 frontmatter 与正文。"""
#     match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content, re.DOTALL)
#     if not match:
#         return {}, content.strip()

#     meta_raw = match.group(1)
#     body = match.group(2).strip()
#     meta: dict[str, str] = {}

#     for line in meta_raw.splitlines():
#         line = line.strip()
#         if not line or line.startswith("#") or ":" not in line:
#             continue
#         key, value = line.split(":", 1)
#         meta[key.strip()] = value.strip().strip('"').strip("'")

#     return meta, body


# def scan_skills(skill_paths: list[Path] | None = None) -> list[SkillMetadata]:
#     """扫描可用 Skills。"""
#     paths = skill_paths or DEFAULT_SKILL_PATHS
#     found: list[SkillMetadata] = []
#     seen_names: set[str] = set()

#     for base in paths:
#         if not base.exists() or not base.is_dir():
#             continue

#         for skill_dir in sorted(base.iterdir()):
#             if not skill_dir.is_dir():
#                 continue

#             skill_md = skill_dir / "SKILL.md"
#             if not skill_md.exists():
#                 continue

#             try:
#                 content = skill_md.read_text(encoding="utf-8")
#             except Exception:
#                 continue

#             meta, _ = _extract_frontmatter(content)
#             name = meta.get("name") or skill_dir.name
#             description = meta.get("description") or "无描述"

#             if not name or name in seen_names:
#                 continue

#             found.append(
#                 SkillMetadata(
#                     name=name,
#                     description=description,
#                     skill_path=skill_dir,
#                     skill_md_path=skill_md,
#                 )
#             )
#             seen_names.add(name)

#     return found


# def build_skills_catalog_prompt() -> str:
#     """构建可注入系统消息的 Skills 列表提示。"""
#     skills = scan_skills()
#     if not skills:
#         return ""

#     lines = [
#         "## 可用 Skills",
#         "",
#         "当用户需求与以下技能描述匹配时，先调用 load_skill(skill_name) 读取详细指令，再继续执行。",
#         "",
#     ]

#     for skill in skills:
#         lines.append(f"- `{skill.name}`: {skill.description}")

#     lines.extend(
#         [
#             "",
#             "Skill 指令里若包含脚本执行步骤，可调用 bash 工具执行。",
#             "调用 load_skill 之后，不要只做摘要，必须基于 Skill 指令继续执行至少一个可验证动作。",
#             "若 Skill 指令包含可执行脚本，下一步优先调用 bash 执行对应脚本。",
#             "仅在技能确实相关时调用 load_skill，避免无关加载。",
#         ]
#     )

#     return "\n".join(lines)


# @tool
# def load_skill(skill_name: str) -> str:
#     """加载指定 Skill 的完整指令（SKILL.md 正文）。"""
#     writer = get_stream_writer()
#     writer({"type": "status", "content": f"🧩 正在加载 Skill: {skill_name}"})

#     skills = scan_skills()
#     if not skills:
#         return "Skill 不可用：未发现任何 Skill 目录。"

#     target = next((s for s in skills if s.name == skill_name), None)
#     if target is None:
#         target = next((s for s in skills if s.name.lower() == skill_name.lower()), None)

#     if target is None:
#         available = ", ".join(s.name for s in skills)
#         return f"Skill '{skill_name}' 不存在。可用 Skills: {available}"

#     try:
#         full_content = target.skill_md_path.read_text(encoding="utf-8")
#     except Exception as e:
#         return f"读取 Skill 失败: {e}"

#     _, instructions = _extract_frontmatter(full_content)
#     scripts_dir = target.skill_path / "scripts"

#     return (
#         f"# Skill: {target.name}\n\n"
#         f"## Instructions\n\n{instructions}\n\n"
#         f"## Skill Path Info\n\n"
#         f"- Skill Directory: {target.skill_path}\n"
#         f"- Scripts Directory: {scripts_dir}\n\n"
#         "执行脚本时优先使用绝对路径，例如:\n"
#         f"uv run {scripts_dir}/script_name.py [args]\n\n"
#         "## Next Step (Required)\n"
#         "你已成功加载该 Skill。下一步必须基于以上 Instructions 继续执行，"
#         "至少完成一个可验证动作（例如调用 bash 执行脚本或读取 Skill 相关文件），"
#         "不要在未执行的情况下直接结束。"
#     )


# @tool
# def bash(command: str) -> str:
#     """执行 shell 命令（默认工作目录为 backend 目录）。"""
#     writer = get_stream_writer()
#     writer({"type": "status", "content": f"💻 执行命令: {command[:80]}"})

#     backend_dir = Path(__file__).resolve().parents[4]

#     try:
#         result = subprocess.run(
#             command,
#             shell=True,
#             cwd=str(backend_dir),
#             capture_output=True,
#             text=True,
#             timeout=300,
#         )

#         parts: list[str] = []
#         if result.returncode == 0:
#             parts.append("[OK]")
#         else:
#             parts.append(f"[FAILED] Exit code: {result.returncode}")

#         parts.append("")

#         if result.stdout:
#             parts.append(result.stdout.rstrip())

#         if result.stderr:
#             if result.stdout:
#                 parts.append("")
#             parts.append("--- stderr ---")
#             parts.append(result.stderr.rstrip())

#         if not result.stdout and not result.stderr:
#             parts.append("(no output)")

#         return "\n".join(parts)

#     except subprocess.TimeoutExpired:
#         return "[FAILED] Command timed out after 300 seconds."
#     except Exception as e:
#         return f"[FAILED] {e}"
