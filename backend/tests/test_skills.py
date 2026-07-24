import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from app.services.agent import skills


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
