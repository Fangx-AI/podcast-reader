import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"


class BundleAndOutputTests(unittest.TestCase):
    def invoke(self, name, *args):
        result = subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)], text=True, capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        return json.loads(result.stdout)

    def test_local_transcript_one_shot_bundle_and_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            exact = Path(folder) / "episode"
            first = self.invoke("prepare_episode.py", FIXTURES / "sample.srt", "--output-dir", exact)
            self.assertEqual(first["status"], "ready_for_analysis")
            self.assertTrue((exact / "bundle.json").is_file())
            self.assertTrue((exact / "chunks.json").is_file())
            validated = self.invoke("validate_bundle.py", exact)
            self.assertTrue(validated["valid"])
            second = self.invoke("prepare_episode.py", FIXTURES / "sample.srt", "--output-dir", exact)
            self.assertEqual(second["cache"], "reused")

    def test_zero_key_doctor_is_offline_and_machine_readable(self):
        with tempfile.TemporaryDirectory() as folder:
            result = self.invoke("doctor.py", "--output-root", folder, "--json")
            self.assertFalse(result["api_key_required"])
            self.assertFalse(result["network_used"])
            self.assertTrue(result["capabilities"]["transcript_and_index"])

    def test_cross_platform_installer_copies_a_valid_skill(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "skills"
            result = self.invoke("install_skill.py", "--target", target, "--json")
            installed = target / "podcast-reader"
            self.assertEqual(result["status"], "installed")
            self.assertTrue((installed / "SKILL.md").is_file())
            self.assertTrue((installed / "scripts" / "doctor.py").is_file())
            self.assertFalse(any(installed.rglob("*.pyc")))

    def test_unified_process_entrypoint_handles_local_transcript(self):
        with tempfile.TemporaryDirectory() as folder:
            exact = Path(folder) / "episode"
            result = self.invoke("process_episode.py", FIXTURES / "sample.srt", "--output-dir", exact)
            self.assertEqual(result["status"], "ready_for_analysis")
            self.assertFalse(result["api_key_required"])
            self.assertTrue((exact / "progress.json").is_file())
            self.assertTrue((exact / "transcript-quality.json").is_file())
            self.assertTrue((exact / "analysis-handoff.json").is_file())

    def test_golden_markdown_is_strictly_valid(self):
        result = self.invoke("validate_notes.py", FIXTURES / "golden-analysis.md", "--strict")
        self.assertTrue(result["valid"])

    def test_finalize_marks_valid_bundle_analyzed(self):
        with tempfile.TemporaryDirectory() as folder:
            exact = Path(folder) / "episode"
            self.invoke("prepare_episode.py", FIXTURES / "sample.srt", "--output-dir", exact)
            shutil.copy2(FIXTURES / "golden-analysis.md", exact / "analysis.md")
            shutil.copy2(FIXTURES / "golden-evidence.json", exact / "evidence.json")
            result = self.invoke("finalize_bundle.py", exact)
            self.assertTrue(result["valid"])
            self.assertEqual(result["status"], "analyzed")
            bundle = json.loads((exact / "bundle.json").read_text(encoding="utf-8"))
            self.assertEqual(bundle["status"], "analyzed")
            self.assertIn("analysis.md", bundle["artifacts"]["analysis"])
            self.assertNotIn("analyze transcript", bundle["next_actions"])

    def test_evidence_csv_export(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "evidence.json"
            source.write_text(json.dumps({"claims": [{"claim": "测试主张", "kind": "opinion", "evidence": [{"start": "00:00:01", "end": "00:00:03"}]}]}, ensure_ascii=False), encoding="utf-8")
            result = self.invoke("export_evidence.py", source)
            self.assertIn("claims", result["exports"])
            self.assertTrue((root / "claims.csv").read_bytes().startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
