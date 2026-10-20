"""Exercise the complete default summary flow and reuse boundaries offline."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from finalize_bundle import finalize
from validate_bundle import validate


class SummaryPipelineTests(unittest.TestCase):
    def invoke(self, name, *args):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / name), *map(str, args)],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return json.loads(result.stdout)

    def prepare(self, root, *, language="zh-CN"):
        episode = root / "episode"
        result = self.invoke("process_episode.py", FIXTURES / "summary-demo.srt",
                             "--output-dir", episode, "--output-language", language)
        self.assertEqual(result["status"], "ready_for_analysis")
        shutil.copy2(FIXTURES / "summary-demo-evidence.json", episode / "evidence.json")
        return episode

    def test_default_flow_requires_agent_then_generates_both_deliverables(self):
        with tempfile.TemporaryDirectory() as folder:
            episode = self.prepare(Path(folder))
            handoff = json.loads((episode / "analysis-handoff.json").read_text(encoding="utf-8"))
            self.assertEqual(handoff["mode"], "summary")
            self.assertEqual(handoff["required_outputs"], {"evidence": "evidence.json"})
            self.assertIn("whole_episode", handoff["summary_contract"])
            self.assertFalse((episode / "summary.md").exists())
            result = finalize(episode)
            self.assertTrue(result["valid"], result)
            self.assertTrue(validate(episode)["valid"], validate(episode))
            summary = (episode / "summary.md").read_text(encoding="utf-8")
            self.assertIn("关键问题", summary)
            self.assertIn("高价值信息", summary)
            self.assertIn("仍未解决", summary)
            self.assertNotIn("主张账本", summary)
            self.assertEqual(summary, (episode / "analysis.md").read_text(encoding="utf-8"))
            self.assertTrue((episode / "reader.html").is_file())
            reused = self.invoke("process_episode.py", FIXTURES / "summary-demo.srt",
                                  "--output-dir", episode, "--output-language", "zh-CN")
            self.assertEqual(reused["status"], "analyzed")
            self.assertIsNone(reused["analysis_handoff"])
            self.assertTrue(reused["summary"].endswith("summary.md"))

    def test_new_language_and_missing_summary_reopen_agent_handoff(self):
        with tempfile.TemporaryDirectory() as folder:
            episode = self.prepare(Path(folder))
            self.assertTrue(finalize(episode)["valid"])
            (episode / "summary.md").unlink()
            result = self.invoke("process_episode.py", FIXTURES / "summary-demo.srt",
                                 "--output-dir", episode, "--output-language", "zh-CN")
            self.assertEqual(result["status"], "ready_for_analysis")
            self.assertTrue(finalize(episode)["valid"])
            changed = self.invoke("process_episode.py", FIXTURES / "summary-demo.srt",
                                  "--output-dir", episode, "--output-language", "en")
            self.assertEqual(changed["status"], "ready_for_analysis")
            bundle = json.loads((episode / "bundle.json").read_text(encoding="utf-8"))
            self.assertEqual(bundle["output_language"], "en")
            self.assertNotIn("completed_at", bundle)

    def test_legacy_analyzed_cache_is_upgraded_without_retranscription(self):
        with tempfile.TemporaryDirectory() as folder:
            episode = Path(folder) / "episode"
            self.invoke("prepare_episode.py", FIXTURES / "sample.srt", "--output-dir", episode)
            for name in ("analysis.md", "evidence.json"):
                shutil.copy2(FIXTURES / f"golden-{name}", episode / name)
            self.assertTrue(finalize(episode)["valid"])
            before = (episode / "transcript.json").read_bytes()
            result = self.invoke("process_episode.py", FIXTURES / "sample.srt", "--output-dir", episode)
            self.assertEqual(result["status"], "ready_for_analysis")
            self.assertEqual(before, (episode / "transcript.json").read_bytes())
            failed = finalize(episode)
            self.assertFalse(failed["valid"])

    def test_invalid_digest_never_creates_finished_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            episode = self.prepare(Path(folder))
            evidence = json.loads((episode / "evidence.json").read_text(encoding="utf-8"))
            evidence["digest"]["quick_takes"][0]["evidence"][0]["segment_ids"] = [999]
            (episode / "evidence.json").write_text(json.dumps(evidence), encoding="utf-8")
            self.assertFalse(finalize(episode)["valid"])
            self.assertFalse((episode / "summary.md").exists())
            self.assertFalse((episode / "reader.html").exists())
            state = json.loads((episode / "bundle.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "ready_for_analysis")

    def test_reader_failure_does_not_mark_bundle_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            episode = self.prepare(Path(folder))
            with patch("finalize_bundle.render_reader", side_effect=OSError("disk unavailable")):
                self.assertFalse(finalize(episode)["valid"])
            bundle = json.loads((episode / "bundle.json").read_text(encoding="utf-8"))
            self.assertEqual(bundle["status"], "ready_for_analysis")

    def test_modified_summary_is_rejected_until_regenerated(self):
        with tempfile.TemporaryDirectory() as folder:
            episode = self.prepare(Path(folder))
            self.assertTrue(finalize(episode)["valid"])
            with (episode / "summary.md").open("a", encoding="utf-8") as stream:
                stream.write("\nAn unsupported conclusion.\n")
            self.assertFalse(validate(episode)["valid"])

    def test_share_reader_contains_summary_without_embedded_transcript(self):
        with tempfile.TemporaryDirectory() as folder:
            episode = self.prepare(Path(folder))
            self.assertTrue(finalize(episode)["valid"])
            exported = self.invoke("export_bundle.py", episode, "--profile", "share")
            with zipfile.ZipFile(exported["output"]) as archive:
                names = archive.namelist()
                self.assertNotIn("podcast-reader-bundle/transcript.json", names)
                page = archive.read("podcast-reader-bundle/reader.html").decode("utf-8")
                self.assertIn("高价值信息", page)
                self.assertNotIn("这是我们创作的一段演示对话", page)
                self.assertNotIn('class="segment"', page)

    def test_corrupt_reader_is_not_returned_as_finished_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            episode = self.prepare(Path(folder))
            self.assertTrue(finalize(episode)["valid"])
            (episode / "reader.html").write_text("", encoding="utf-8")
            self.assertFalse(validate(episode)["valid"])
            result = self.invoke("process_episode.py", FIXTURES / "summary-demo.srt",
                                 "--output-dir", episode, "--output-language", "zh-CN")
            self.assertEqual(result["status"], "ready_for_analysis")
            self.assertIsNone(result["reader"])

    def test_untimed_text_can_finish_without_invented_timestamps(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            text = root / "source.txt"
            text.write_text("先选任务，再选工具。结果必须可以检查。", encoding="utf-8")
            episode = root / "episode"
            self.invoke("process_episode.py", text, "--output-dir", episode)
            evidence = json.loads((FIXTURES / "summary-demo-evidence.json").read_text(encoding="utf-8"))
            evidence["episode"] = {"title": "一段建议", "source_url": None}
            evidence["summary"] = "先选能检查结果的任务。"
            evidence["digest"] = {
                "headline": "先选能检查结果的任务",
                "takeaway": "先选任务，再选工具。",
                "evidence": [{"segment_ids": [1]}],
                "quick_takes": [{"question": "先选什么？", "answer": "先选能检查结果的任务。", "evidence": [{"segment_ids": [1]}]}],
                "insights": [{"title": "验收先行", "summary": "结果必须能检查。", "evidence": [{"segment_ids": [1]}]}],
            }
            evidence["chapters"] = []
            evidence["quotes"] = []
            evidence["limitations"] = ["来源是无时间戳文本。"]
            (episode / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")
            result = finalize(episode)
            self.assertTrue(result["valid"], result)
            self.assertTrue(validate(episode)["valid"], validate(episode))
            markdown = (episode / "summary.md").read_text(encoding="utf-8")
            self.assertNotIn("[00:00:00", markdown)
            self.assertIn("#1", markdown)


if __name__ == "__main__":
    unittest.main()
