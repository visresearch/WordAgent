import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from app.services.agent import skills


class LoadSkillContextTests(unittest.TestCase):
    def test_loads_all_markdown_content_without_truncation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            skills_root = Path(temp_dir_str) / "skills"
            skill_dir = skills_root / "long-skill"
            skill_dir.mkdir(parents=True)

            skill_tail = "SKILL_BODY_END"
            reference_tail = "REFERENCE_BODY_END"
            (skill_dir / "SKILL.md").write_text(
                "---\nname: Long Skill\ndescription: Complete content test\n---\n" + "A" * 13000 + skill_tail,
                encoding="utf-8",
            )
            (skill_dir / "reference.md").write_text(
                "B" * 4000 + reference_tail,
                encoding="utf-8",
            )

            with (
                patch.object(skills, "_skills_root", return_value=skills_root),
                patch.object(skills, "_load_skill_enable_map", return_value={}),
            ):
                context = skills.load_skill_context("long-skill")

            self.assertIn(skill_tail, context)
            self.assertIn(reference_tail, context)
            self.assertGreater(len(context), 17000)

    def test_skills_prompt_keeps_complete_trigger_description(self) -> None:
        description = (
            "Replicate formatting from a reference document. "
            "Use when the user asks to strictly follow a graduation thesis template."
        )
        discovered = [
            {
                "name": "document-format-replication",
                "folder": "document-format-replication",
                "description": description,
                "enabled": True,
            }
        ]

        with patch.object(skills, "discover_skills", return_value=discovered):
            prompt = skills.build_skills_prompt()

        self.assertIn(description, prompt)
        self.assertNotIn("...", prompt)


class InstallSkillZipTests(unittest.TestCase):
    def test_rejects_existing_skill_without_overwriting_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            skills_root = temp_dir / "skills"
            existing = skills_root / "writing-helper"
            existing.mkdir(parents=True)
            existing_skill = existing / "SKILL.md"
            existing_skill.write_text("existing content", encoding="utf-8")

            archive = temp_dir / "Writing-Helper.zip"
            with zipfile.ZipFile(archive, "w") as zip_file:
                zip_file.writestr("Writing-Helper/SKILL.md", "new content")

            with (
                patch.object(skills, "_skills_root", return_value=skills_root),
                self.assertRaisesRegex(
                    skills.SkillAlreadyExistsError,
                    "请先删除该同名 Skill",
                ),
            ):
                skills.install_skill_zip(archive)

            self.assertEqual(existing_skill.read_text(encoding="utf-8"), "existing content")
            self.assertFalse((skills_root / "Writing-Helper").exists())

    def test_rejects_duplicate_frontmatter_name_with_different_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            skills_root = temp_dir / "skills"
            existing = skills_root / "old-folder"
            existing.mkdir(parents=True)
            existing_skill = existing / "SKILL.md"
            existing_skill.write_text("---\nname: Writing Helper\n---\nexisting", encoding="utf-8")

            archive = temp_dir / "new-folder.zip"
            with zipfile.ZipFile(archive, "w") as zip_file:
                zip_file.writestr("new-folder/SKILL.md", "---\nname: writing helper\n---\nnew")

            with (
                patch.object(skills, "_skills_root", return_value=skills_root),
                patch.object(skills, "_load_skill_enable_map", return_value={}),
                self.assertRaises(skills.SkillAlreadyExistsError),
            ):
                skills.install_skill_zip(archive)

            self.assertIn("existing", existing_skill.read_text(encoding="utf-8"))
            self.assertFalse((skills_root / "new-folder").exists())


class SyncBuiltinSkillsTests(unittest.TestCase):
    def _write_skill(self, root: Path, folder: str, name: str, body: str = "content") -> Path:
        skill_dir = root / folder
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Test skill\n---\n{body}",
            encoding="utf-8",
        )
        return skill_dir

    def test_copies_missing_builtin_skills_and_enables_them(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            source_root = temp_dir / "builtin"
            skills_root = temp_dir / "skills"
            source_skill = self._write_skill(source_root, "doc-helper", "doc-helper")
            (source_skill / "reference.md").write_text("reference", encoding="utf-8")
            skills_root.mkdir()

            with (
                patch.object(skills, "get_builtin_skills_dir", return_value=source_root),
                patch.object(skills, "_skills_root", return_value=skills_root),
                patch.object(skills, "_load_skill_enable_map", return_value={}),
                patch.object(skills, "set_skill_enabled") as set_enabled,
            ):
                result = skills.sync_builtin_skills()

            self.assertEqual(result, {"copied": ["doc-helper"], "skipped": [], "invalid": []})
            self.assertEqual(
                (skills_root / "doc-helper" / "reference.md").read_text(encoding="utf-8"),
                "reference",
            )
            set_enabled.assert_called_once_with("doc-helper", True)

    def test_refreshes_existing_builtin_files_without_resetting_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            source_root = temp_dir / "builtin"
            skills_root = temp_dir / "skills"
            self._write_skill(source_root, "doc-helper", "doc-helper", "builtin")
            existing = self._write_skill(skills_root, "DOC-HELPER", "custom-helper", "old bundled content")
            (existing / "user-notes.md").write_text("keep me", encoding="utf-8")

            with (
                patch.object(skills, "get_builtin_skills_dir", return_value=source_root),
                patch.object(skills, "_skills_root", return_value=skills_root),
                patch.object(skills, "_load_skill_enable_map", return_value={"DOC-HELPER": False}),
                patch.object(skills, "set_skill_enabled") as set_enabled,
            ):
                result = skills.sync_builtin_skills()

            self.assertEqual(result, {"copied": [], "skipped": ["doc-helper"], "invalid": []})
            self.assertIn("builtin", (existing / "SKILL.md").read_text(encoding="utf-8"))
            self.assertEqual((existing / "user-notes.md").read_text(encoding="utf-8"), "keep me")
            set_enabled.assert_not_called()

    def test_skips_duplicate_frontmatter_name_and_invalid_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            source_root = temp_dir / "builtin"
            skills_root = temp_dir / "skills"
            self._write_skill(source_root, "builtin-folder", "Shared Skill")
            (source_root / "invalid-folder").mkdir(parents=True)
            self._write_skill(skills_root, "user-folder", "shared skill", "user content")

            with (
                patch.object(skills, "get_builtin_skills_dir", return_value=source_root),
                patch.object(skills, "_skills_root", return_value=skills_root),
                patch.object(skills, "_load_skill_enable_map", return_value={}),
                patch.object(skills, "set_skill_enabled") as set_enabled,
            ):
                result = skills.sync_builtin_skills()

            self.assertEqual(
                result,
                {
                    "copied": [],
                    "skipped": ["builtin-folder"],
                    "invalid": ["invalid-folder"],
                },
            )
            self.assertFalse((skills_root / "builtin-folder").exists())
            set_enabled.assert_not_called()

    def test_discovery_marks_bundled_skill_as_builtin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            source_root = temp_dir / "builtin"
            skills_root = temp_dir / "skills"
            self._write_skill(source_root, "doc-helper", "Doc Helper", "bundled")
            self._write_skill(skills_root, "doc-helper", "Doc Helper", "installed")
            self._write_skill(skills_root, "user-helper", "User Helper", "custom")

            with (
                patch.object(skills, "get_builtin_skills_dir", return_value=source_root),
                patch.object(skills, "_skills_root", return_value=skills_root),
                patch.object(skills, "_load_skill_enable_map", return_value={}),
            ):
                discovered = skills.discover_skills(include_disabled=True)

            by_folder = {str(item["folder"]): item for item in discovered}
            self.assertTrue(by_folder["doc-helper"]["builtin"])
            self.assertFalse(by_folder["user-helper"]["builtin"])


class OpenSkillDirectoryTests(unittest.TestCase):
    def test_opens_valid_skill_directory_with_linux_file_manager(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_str:
            skills_root = Path(temp_dir_str) / "skills"
            skill_dir = skills_root / "writing-helper"
            skill_dir.mkdir(parents=True)

            with (
                patch.object(skills, "_skills_root", return_value=skills_root),
                patch.object(skills.sys, "platform", "linux"),
                patch.object(skills.subprocess, "Popen") as popen,
            ):
                opened_path = skills.open_skill_directory("writing-helper")

            self.assertEqual(opened_path, skill_dir.resolve())
            popen.assert_called_once_with(
                ["xdg-open", str(skill_dir.resolve())],
                stdout=skills.subprocess.DEVNULL,
                stderr=skills.subprocess.DEVNULL,
                start_new_session=True,
            )


if __name__ == "__main__":
    unittest.main()
