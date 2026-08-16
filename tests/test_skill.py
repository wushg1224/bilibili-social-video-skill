from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "download-bilibili-video"


class SkillStructureTests(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        self.assertTrue((SKILL_DIR / "SKILL.md").is_file())
        self.assertTrue((SKILL_DIR / "scripts" / "bilibili_download.py").is_file())
        self.assertTrue((SKILL_DIR / "agents" / "openai.yaml").is_file())

    def test_frontmatter_is_minimal_and_valid(self) -> None:
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
        self.assertIsNotNone(match)
        frontmatter = match.group(1) if match else ""
        keys = [line.split(":", 1)[0] for line in frontmatter.splitlines() if ":" in line]
        self.assertEqual(keys, ["name", "description"])
        self.assertIn("name: download-bilibili-video", frontmatter)
        self.assertLess(len(text.splitlines()), 500)


if __name__ == "__main__":
    unittest.main()
