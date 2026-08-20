import re
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SkillQualityTests(unittest.TestCase):
    def test_skill_manifest_and_progressive_disclosure(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\nname: podcast-reader\n"))
        self.assertRegex(text, r"(?m)^description:\s+\S")
        self.assertLess(len(text.splitlines()), 500)
        self.assertNotIn("python scripts/", text)
        self.assertIn("{skill_dir}/scripts/prepare_episode.py", text)
        for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
            if "://" not in target:
                self.assertTrue((ROOT / target).is_file(), msg=f"broken SKILL.md link: {target}")

    def test_agent_metadata_invokes_skill(self):
        text = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("$podcast-reader", text)
        self.assertIn("display_name:", text)
        for target in re.findall(r'icon_(?:small|large):\s*"([^"]+)"', text):
            self.assertTrue((ROOT / target).is_file(), msg=f"missing agent icon: {target}")

    def test_every_cli_has_working_help(self):
        for script in sorted((ROOT / "scripts").glob("*.py")):
            result = subprocess.run([sys.executable, str(script), "--help"], text=True, capture_output=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, msg=f"{script.name}: {result.stderr}")
            self.assertIn("usage:", result.stdout.casefold())


if __name__ == "__main__":
    unittest.main()
