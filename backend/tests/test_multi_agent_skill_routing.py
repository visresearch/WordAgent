import unittest

from app.services.multi_agent import prompts
from app.services.multi_agent.tools import WRITER_TOOLS


class MultiAgentSkillRoutingTests(unittest.TestCase):
    def tearDown(self) -> None:
        prompts.update_skills_prompt("")

    def test_writer_has_load_skill_context_tool(self) -> None:
        self.assertIn("load_skill_context", {tool.name for tool in WRITER_TOOLS})

    def test_writer_prompt_receives_available_skills(self) -> None:
        skill_prompt = (
            "Discovered local skills:\n"
            "- document-format-replication (folder: document-format-replication): Replicate a template."
        )
        prompts.update_skills_prompt(skill_prompt)

        writer_prompt = prompts.get_agent_prompt("writer")

        self.assertIn("document-format-replication", writer_prompt)
        self.assertIn("call `load_skill_context`", writer_prompt)

    def test_planner_requires_matching_skill_in_workflow(self) -> None:
        prompts.update_skills_prompt(
            "- document-format-replication (folder: document-format-replication): Replicate a template."
        )

        planner_prompt = prompts.get_agent_prompt("planner")

        self.assertIn("document-format-replication", planner_prompt)
        self.assertIn("workflow MUST explicitly load it", planner_prompt)


if __name__ == "__main__":
    unittest.main()
