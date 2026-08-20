from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from resolve_podcast import parse_html, parse_rss, resolve_input


class ResolveTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = ROOT / "tests" / "fixtures"

    def test_rss_exact_selection_and_transcript(self):
        result = parse_rss((self.fixtures / "sample.rss").read_bytes(), "https://example.com/feed.xml", "第一期：证据与产品")
        self.assertEqual(result["kind"], "rss")
        self.assertEqual(result["episode"]["guid"], "episode-001")
        self.assertEqual(result["audio_url"], "https://cdn.example.com/episode-001.mp3")
        self.assertEqual(result["transcript_urls"], ["https://cdn.example.com/episode-001.vtt"])

    def test_html_attribute_order_and_deduplication(self):
        result = parse_html((self.fixtures / "sample-page.html").read_bytes(), "https://example.com/episodes/1")
        self.assertEqual(result["title"], "示例节目页")
        self.assertEqual(result["audio_candidates"], ["https://cdn.example.com/audio.mp3"])
        self.assertEqual(result["feed_candidates"], ["https://example.com/feed.xml"])
        self.assertEqual(result["transcript_candidates"], ["https://example.com/transcript.vtt"])

    def test_platform_classification_is_offline(self):
        self.assertEqual(resolve_input("https://www.bilibili.com/video/BV1xx411c7mD", no_network=True)["kind"], "bilibili")
        self.assertEqual(resolve_input("https://youtu.be/dQw4w9WgXcQ", no_network=True)["kind"], "youtube")


if __name__ == "__main__":
    unittest.main()
