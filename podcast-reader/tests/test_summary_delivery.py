"""Protect source provenance and the actual files a listener receives."""

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from export_bundle import export, sanitize_text, sanitized_url
from finalize_bundle import finalize
from prepare_episode import ensure_source_record
from validate_bundle import validate


class HiddenSummaryParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_summary = False
        self.summary = []
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag == "pre" and dict(attrs).get("id") == "summary-markdown":
            self.in_summary = True

    def handle_endtag(self, tag):
        if tag == "pre":
            self.in_summary = False

    def handle_data(self, value):
        if self.in_summary:
            self.summary.append(value)


class SummaryDeliveryTests(unittest.TestCase):
    def invoke(self, script, *args):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
            text=True, capture_output=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return json.loads(result.stdout)

    def episode(self, root):
        episode = root / "episode"
        self.invoke("process_episode.py", ROOT / "tests/fixtures/summary-demo.srt", "--output-dir", episode)
        evidence = json.loads((ROOT / "tests/fixtures/summary-demo-evidence.json").read_text(encoding="utf-8"))
        evidence["episode"]["source_url"] = "https://www.youtube.com/watch?v=demo&token=SECRET123#t=90"
        (episode / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")
        self.assertTrue(finalize(episode)["valid"])
        return episode

    def test_text_sanitizer_preserves_web_links_and_normal_drive_mentions(self):
        root = Path("C:/private/output")
        text = (
            '<a href="https://example.com/Users/episode?part=2&amp;signature=PRIVATE#t=90">Listen</a>\n'
            "[Listen](<https://example.com/episode#chapter-2>)\n"
            "C: is the system drive; ratio C:D is ordinary text.\n"
            r"File C:\Users\private\episode.txt"
        )
        result = sanitize_text(text, root)
        self.assertIn('href="https://example.com/Users/episode?part=2#t=90"', result)
        self.assertIn("[Listen](<https://example.com/episode#chapter-2>)", result)
        self.assertIn("C: is the system drive; ratio C:D", result)
        self.assertNotIn("PRIVATE", result)
        self.assertNotIn(r"C:\Users", result)
        self.assertNotIn("http[LOCAL_PATH_REDACTED]", result)
        self.assertEqual(
            sanitized_url("https://user:password@example.com/episode?v=1&token=private#t=90"),
            "https://example.com/episode?v=1#t=90",
        )
        self.assertEqual(sanitize_text("https://[2001:db8::1]", root), "https://[2001:db8::1]")
        escaped_markdown_url = "&lt;https://example.com/episode?episode=42&gt;"
        self.assertEqual(sanitize_text(escaped_markdown_url, root), escaped_markdown_url)
        escaped_attack = '<a href="https://example.com/&quot;&gt;&lt;svg/onload=alert(1)&gt;">Listen</a>'
        self.assertEqual(sanitize_text(escaped_attack, root), escaped_attack)

    def test_share_preserves_source_and_seek_links_and_updates_hashes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            episode = self.episode(root)
            output = root / "share.zip"
            export(episode, output, "share", False)
            with zipfile.ZipFile(output) as archive:
                prefix = "podcast-reader-bundle/"
                page = archive.read(prefix + "reader.html").decode("utf-8")
                markdown = archive.read(prefix + "summary.md").decode("utf-8")
                self.assertIn("https://www.youtube.com/watch?v=demo", page)
                self.assertIn("t=30s", page)
                self.assertIn("#t=90", markdown)
                self.assertNotIn('class="segment"', page)
                self.assertNotIn("http[LOCAL_PATH_REDACTED]", page + markdown)
                parsed = HiddenSummaryParser()
                parsed.feed(page)
                self.assertEqual("".join(parsed.summary), markdown)
                contents = [archive.read(name) for name in archive.namelist()]
                self.assertFalse(any(b"SECRET123" in value for value in contents))
                bundle = json.loads(archive.read(prefix + "bundle.json"))
                for name in ("summary.md", "reader.html"):
                    self.assertEqual(bundle["deliverable_hashes"][name], hashlib.sha256(archive.read(prefix + name)).hexdigest())

    def test_html_export_does_not_reactivate_escaped_source_markup(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            episode = self.episode(root)
            evidence_path = episode / "evidence.json"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence["episode"]["source_url"] = 'https://example.com/"><svg/onload=alert(1)>'
            evidence_path.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")
            self.assertTrue(finalize(episode)["valid"])
            output = root / "escaped.zip"
            export(episode, output, "share", False)
            with zipfile.ZipFile(output) as archive:
                page = archive.read("podcast-reader-bundle/reader.html").decode("utf-8")
                markdown = archive.read("podcast-reader-bundle/summary.md").decode("utf-8")
                parsed = HiddenSummaryParser()
                parsed.feed(page)
                self.assertNotIn("svg", parsed.tags)
                self.assertNotIn("<svg", page)
                self.assertEqual("".join(parsed.summary), markdown)

    def test_unfinished_and_stale_bundles_cannot_be_shared(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            episode = self.episode(root)
            with (episode / "summary.md").open("a", encoding="utf-8") as stream:
                stream.write("Stale extra text")
            for profile in ("share", "portable"):
                output = root / f"{profile}.zip"
                with self.assertRaisesRegex(ValueError, "incomplete or stale"):
                    export(episode, output, profile, False)
                self.assertFalse(output.exists())
            bundle = json.loads((episode / "bundle.json").read_text(encoding="utf-8"))
            bundle["status"] = "ready_for_analysis"
            (episode / "bundle.json").write_text(json.dumps(bundle), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Complete the summary"):
                export(episode, root / "unfinished.zip", "share", False)
            self.assertEqual(export(episode, root / "backup.zip", "archive", False)["status"], "exported")

    def test_portable_full_transcript_export_can_be_verified_after_extraction(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            episode = self.episode(root)
            output = root / "portable.zip"
            export(episode, output, "portable", True)
            unpacked = root / "unpacked"
            with zipfile.ZipFile(output) as archive:
                archive.extractall(unpacked)
            result = validate(unpacked / "podcast-reader-bundle")
            self.assertTrue(result["valid"], result)

    def test_missing_transcript_cannot_silently_produce_a_share_page(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            episode = self.episode(root)
            (episode / "transcript.json").unlink()
            with self.assertRaisesRegex(ValueError, "transcript.json"):
                export(episode, root / "missing.zip", "share", False)
            self.assertFalse((root / "missing.zip").exists())

    def test_source_record_updates_when_output_directory_changes_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            episode = root / "episode"
            first, second = root / "first.txt", root / "second.txt"
            first.write_text("First source.", encoding="utf-8")
            second.write_text("Second source.", encoding="utf-8")
            for source in (first, second):
                self.invoke("prepare_episode.py", source, "--output-dir", episode)
            source_record = json.loads((episode / "source.json").read_text(encoding="utf-8"))
            bundle = json.loads((episode / "bundle.json").read_text(encoding="utf-8"))
            self.assertEqual(source_record["source"], str(second))
            self.assertEqual(source_record["source"], bundle["source_input"])

    def test_same_source_resume_preserves_richer_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            url = "https://www.youtube.com/watch?v=demo"
            original = {"source_url": url, "title": "Full publisher title", "show_or_uploader": "Author", "duration_seconds": 360, "retrieved_at": "original-time"}
            (root / "source.json").write_text(json.dumps(original), encoding="utf-8")
            ensure_source_record(root, url, {"kind": "youtube", "title": None})
            saved = json.loads((root / "source.json").read_text(encoding="utf-8"))
            for key, value in original.items():
                self.assertEqual(saved[key], value)
            self.assertIn("source_identity", saved)

    def test_different_selected_feed_episode_updates_source_record(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            url = "https://example.com/feed.xml"
            ensure_source_record(root, url, {"kind": "rss", "episode": {"guid": "A", "title": "Episode A"}})
            ensure_source_record(root, url, {"kind": "rss", "episode": {"guid": "B", "title": "Episode B"}})
            saved = json.loads((root / "source.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["title"], "Episode B")

    def test_feed_query_change_cannot_reuse_the_previous_episode_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            feed = ROOT / "tests/fixtures/sample.rss"
            first = self.invoke("prepare_episode.py", feed, "--output-dir", root, "--mode", "metadata", "--query", "episode-001")
            second = self.invoke("prepare_episode.py", feed, "--output-dir", root, "--mode", "metadata", "--query", "episode-002")
            self.assertEqual(first["resolution"]["episode"]["guid"], "episode-001")
            self.assertEqual(second["resolution"]["episode"]["guid"], "episode-002")
            saved = json.loads((root / "source.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["title"], second["resolution"]["episode"]["title"])


if __name__ == "__main__":
    unittest.main()
