"""
Multi-agent prompts loader.
"""

from functools import lru_cache
from pathlib import Path


_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# Cache for dynamic prompts
_mcp_tools_prompt_cache = ""
_skills_prompt_cache = ""


def update_mcp_tools_prompt(prompt: str) -> None:
    """Update the cached MCP tools prompt for research agent."""
    global _mcp_tools_prompt_cache
    _mcp_tools_prompt_cache = prompt


def update_skills_prompt(prompt: str) -> None:
    """Update the cached skills prompt for research agent."""
    global _skills_prompt_cache
    _skills_prompt_cache = prompt


# ============================================================================
# Core prompts by agent role
# ============================================================================

# Common prompts for all agents
_COMMON_PROMPT_FILES = [
    "system-prompt-common-rules.md",
    "system-prompt-output-format.md",
    "system-prompt-output-efficiency.md",
]

_AGENT_PROMPT_FILES = {
    "planner": [
        "agent-prompt-planner.md",
    ],
    "research": [
        "agent-prompt-research.md",
    ],
    "outline": [
        "agent-prompt-outline.md",
    ],
    "writer": [
        "agent-prompt-writer.md",
    ],
    "reviewer": [
        "agent-prompt-reviewer.md",
    ],
}

# Tool usage strategy prompts (file names - will be loaded by _read_prompt_file)
_TOOL_USAGE_FILES = {
    "read_document": "system-prompt-tool-usage-read-document.md",
    "search_document": "system-prompt-tool-usage-search-document.md",
    "generate_document": "system-prompt-tool-usage-generate-document.md",
    "delete_document": "system-prompt-tool-usage-delete-document.md",
    "create_workflow": "system-prompt-tool-usage-create-workflow.md",
    "review_document": "system-prompt-tool-usage-review-document.md",
    "load_skill_context": "system-prompt-tool-usage-load-skill-context.md",
}


# ============================================================================
# Tool description files
# ============================================================================

_TOOL_DESCRIPTION_FILES = {
    "read_document": "tool-description-read-document.md",
    "search_document": "tool-description-search-document.md",
    "generate_document": "tool-description-generate-document.md",
    "delete_document": "tool-description-delete-document.md",
    "create_workflow": "tool-description-create-workflow.md",
    "review_document": "tool-description-review-document.md",
}


@lru_cache(maxsize=64)
def _read_prompt_file(file_name: str) -> str:
    """Read a single markdown prompt file."""
    file_path = _PROMPTS_DIR / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {file_path}")
    return file_path.read_text(encoding="utf-8").strip()


def get_tool_description(tool_name: str) -> str:
    """Get tool description markdown content by tool name."""
    file_name = _TOOL_DESCRIPTION_FILES.get(tool_name)
    if not file_name:
        raise KeyError(f"No description file mapped for tool: {tool_name}")
    return _read_prompt_file(file_name)


def _load_prompt_content(prompt_ref: str) -> str:
    """Load prompt content from file name or return as-is if already content."""
    if not prompt_ref:
        return ""
    # If it's a file name (ends with .md), read the file
    if prompt_ref.endswith(".md"):
        try:
            return _read_prompt_file(prompt_ref)
        except FileNotFoundError:
            return ""
    # Otherwise return as-is (e.g., cached MCP/skills prompt)
    return prompt_ref


def get_agent_prompt(agent_name: str) -> str:
    """Get the complete system prompt for a specific agent."""
    parts = []

    # Common prompts
    for f in _COMMON_PROMPT_FILES:
        try:
            parts.append(_read_prompt_file(f))
        except FileNotFoundError:
            pass

    # Agent-specific prompts
    agent_files = _AGENT_PROMPT_FILES.get(agent_name, [])
    for f in agent_files:
        try:
            parts.append(_read_prompt_file(f))
        except FileNotFoundError:
            pass

    # Tool usage prompts based on available tools
    if agent_name == "planner":
        tool_prompts = [
            _load_prompt_content(_TOOL_USAGE_FILES.get("create_workflow", "")),
        ]
        # Planner needs to know what MCP tools and skills are available for workflow planning
        if _mcp_tools_prompt_cache:
            tool_prompts.append("## Available MCP Tools (for research agent)\n" + _mcp_tools_prompt_cache)
        if _skills_prompt_cache:
            tool_prompts.append("## Available Skills (for research agents)\n" + _skills_prompt_cache)
    elif agent_name == "research":
        tool_prompts = [
            _load_prompt_content(_TOOL_USAGE_FILES.get("load_skill_context", "")),
            _load_prompt_content("system-prompt-tool-usage-mcp-invocation.md"),
        ]
        if _mcp_tools_prompt_cache:
            tool_prompts.append(_mcp_tools_prompt_cache)
        if _skills_prompt_cache:
            tool_prompts.append(_skills_prompt_cache)
    elif agent_name == "outline":
        tool_prompts = [
            _load_prompt_content(_TOOL_USAGE_FILES.get("read_document", "")),
            _load_prompt_content(_TOOL_USAGE_FILES.get("search_document", "")),
        ]
    elif agent_name == "writer":
        tool_prompts = [
            _load_prompt_content(_TOOL_USAGE_FILES.get("read_document", "")),
            _load_prompt_content(_TOOL_USAGE_FILES.get("search_document", "")),
            _load_prompt_content(_TOOL_USAGE_FILES.get("generate_document", "")),
            _load_prompt_content(_TOOL_USAGE_FILES.get("delete_document", "")),
            _load_prompt_content("system-prompt-default-recommend-document-style.md"),
        ]
    elif agent_name == "reviewer":
        tool_prompts = [
            _load_prompt_content(_TOOL_USAGE_FILES.get("review_document", "")),
        ]
    else:
        tool_prompts = []

    for p in tool_prompts:
        if p:
            parts.append(p)

    return "\n\n".join(filter(None, parts))


def get_agent_prompt_parts(agent_name: str) -> list[str]:
    """Get prompt parts list for an agent (for inspection)."""
    parts = []
    for f in _COMMON_PROMPT_FILES:
        try:
            parts.append(_read_prompt_file(f))
        except FileNotFoundError:
            pass
    return parts
