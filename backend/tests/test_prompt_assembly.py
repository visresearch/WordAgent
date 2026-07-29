import unittest
from pathlib import Path

from app.services.agent import prompts as single_prompts
from app.services.agent.subAgents import SUB_AGENTS
from app.services.agent.subAgents.runner import SUB_AGENT_PROMPT_FILES, SUB_AGENT_TOOLS, build_sub_agent_system_prompt
from app.services.agent.tools import AGENT_BASE_TOOLS
from app.services.multi_agent import prompts as multi_prompts


class PromptAssemblyTests(unittest.TestCase):
    def tearDown(self) -> None:
        multi_prompts.update_mcp_tools_prompt("")
        multi_prompts.update_skills_prompt("")

    def test_single_agent_and_ask_mode_are_isolated(self) -> None:
        agent_prompt = single_prompts.get_agent_prompt("agent")
        ask_prompt = single_prompts.get_agent_prompt("ask")

        agent_only_sections = (
            "Default Document Style",
            "generate_document Usage Policy",
            "delete_document Usage Policy",
            "insert_break Usage Policy",
            "Built-in Document Reviewer",
        )
        for section in agent_only_sections:
            self.assertIn(section, agent_prompt)
            self.assertNotIn(section, ask_prompt)

        self.assertNotIn("Use `generate_document` for document content", ask_prompt)
        self.assertNotIn("run_sub_agent Usage Policy", agent_prompt)

    def test_single_agent_has_mandatory_document_reviewer_pass(self) -> None:
        agent_prompt = single_prompts.get_agent_prompt("agent")

        self.assertIn("Mandatory final reviewer pass", agent_prompt)
        self.assertIn('read_document(mode="full")', agent_prompt)
        self.assertIn("pageStart", agent_prompt)
        self.assertIn("pageEnd", agent_prompt)
        self.assertIn("Re-read each corrected range", agent_prompt)

    def test_single_agent_does_not_register_sub_agent_tool(self) -> None:
        self.assertNotIn("run_sub_agent", {tool.name for tool in AGENT_BASE_TOOLS})

    def test_multi_agent_writer_rules_do_not_leak_to_other_roles(self) -> None:
        writer_prompt = multi_prompts.get_agent_prompt("writer")
        self.assertIn("generate_document Usage Policy", writer_prompt)
        self.assertIn("insert_break Usage Policy", writer_prompt)
        self.assertIn("Default Document Style", writer_prompt)

        for role in ("planner", "research", "outline", "reviewer"):
            prompt = multi_prompts.get_agent_prompt(role)
            self.assertNotIn("generate_document Usage Policy", prompt)
            self.assertNotIn("insert_break Usage Policy", prompt)
            self.assertNotIn("Default Document Style", prompt)

    def test_prompts_do_not_restore_conflicting_retry_or_read_rules(self) -> None:
        assembled = "\n".join(
            [single_prompts.get_agent_prompt("agent")]
            + [
                multi_prompts.get_agent_prompt(role)
                for role in ("planner", "research", "outline", "writer", "reviewer")
            ]
        )
        self.assertNotIn("Tool fails | Retry once", assembled)
        self.assertNotIn("Call `read_document` first", assembled)
        self.assertNotIn("Call read_document first", assembled)

    def test_all_sub_agents_are_read_only(self) -> None:
        allowed = {"read_document", "search_document"}
        for tools in SUB_AGENT_TOOLS.values():
            self.assertLessEqual(set(tools), allowed)
        for sub_agent in SUB_AGENTS.values():
            self.assertLessEqual(set(sub_agent.get_allowed_tools()), allowed)

    def test_sub_agent_prompts_load_from_sub_agent_directory(self) -> None:
        backend_dir = Path(__file__).resolve().parents[1]
        new_dir = backend_dir / "app/services/agent/subAgents/prompts"
        old_dir = backend_dir / "app/services/agent/prompts"

        for agent_type, prompt_files in SUB_AGENT_PROMPT_FILES.items():
            prompt = build_sub_agent_system_prompt(agent_type)
            self.assertTrue(prompt)
            for prompt_file in prompt_files:
                self.assertTrue((new_dir / prompt_file).is_file())
                self.assertFalse((old_dir / prompt_file).exists())

    def test_default_document_style_has_one_shared_source(self) -> None:
        backend_dir = Path(__file__).resolve().parents[1]
        shared = backend_dir / "app/services/tools/prompts/system-prompt-default-document-style.md"
        old_single = backend_dir / "app/services/agent/prompts/system-prompt-default-recommend-document-style.md"
        old_multi = backend_dir / "app/services/multi_agent/prompts/system-prompt-default-recommend-document-style.md"

        self.assertTrue(shared.is_file())
        self.assertFalse(old_single.exists())
        self.assertFalse(old_multi.exists())


if __name__ == "__main__":
    unittest.main()
