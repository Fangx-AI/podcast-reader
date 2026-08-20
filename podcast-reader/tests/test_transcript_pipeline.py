import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"


class TranscriptPipelineTests(unittest.TestCase):
    def run_script(self, name, *args, expected=0):
        result = subprocess.run([sys.executable, str(SCRIPTS / name), *map(str, args)], text=True, capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, expected, msg=result.stderr or result.stdout)
        return json.loads(result.stdout)

    def test_normalize_chunk_and_search_multilingual(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            normalized = self.run_script("normalize_transcript.py", FIXTURES / "sample.srt", "--output-dir", output, "--language", "mixed", "--method", "human_captions")
            self.assertEqual(normalized["segment_count"], 3)
            self.assertTrue((output / "transcript.srt").is_file())
            chunked = self.run_script("chunk_transcript.py", output / "transcript.json", "-o", output / "chunks.json", "--max-chars", "200")
            self.assertGreaterEqual(chunked["chunk_count"], 1)
            searched = self.run_script("search_chunks.py", output / "chunks.json", "可靠评估 AI Agent")
            self.assertGreater(searched["hit_count"], 0)
            self.assertIn("评估", searched["hits"][0]["text"])

    def test_duplicate_caption_is_collapsed(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)
            self.run_script("normalize_transcript.py", FIXTURES / "sample.vtt", "--output-dir", output)
            data = json.loads((output / "transcript.json").read_text(encoding="utf-8"))
            self.assertEqual(data["segment_count"], 2)
            self.assertEqual(data["segments"][1]["end"], "00:00:10")

    def test_ass_ttml_and_json3_are_normalized(self):
        samples = {
            "sample.ass": "[Events]\nDialogue: 0,0:00:01.00,0:00:03.00,Default,Alice,0,0,0,,{\\i1}Hello\\Nworld\n",
            "sample.ttml": "<tt xmlns='http://www.w3.org/ns/ttml'><body><div><p begin='1.5s' end='3.0s'>你好 世界</p></div></body></tt>",
            "sample.json3": json.dumps({"events": [{"tStartMs": 1000, "dDurationMs": 2000, "segs": [{"utf8": "Evidence matters"}]}]}),
        }
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, content in samples.items():
                source = root / name
                source.write_text(content, encoding="utf-8")
                output = root / f"out-{source.suffix[1:]}"
                result = self.run_script("normalize_transcript.py", source, "--output-dir", output)
                self.assertEqual(result["segment_count"], 1, msg=name)
                document = json.loads((output / "transcript.json").read_text(encoding="utf-8"))
                self.assertEqual(document["segments"][0]["start"], "00:00:01", msg=name)


if __name__ == "__main__":
    unittest.main()
