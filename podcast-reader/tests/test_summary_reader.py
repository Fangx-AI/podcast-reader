import json
from html.parser import HTMLParser
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from render_reader import render, timestamp_url


class PageStructure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_details = False
        self.details_open = []
        self.source_sections = []
        self.hrefs = []
        self.scripts = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "details":
            self.in_details = True
            self.details_open.append("open" in attrs)
        if tag == "article" and attrs.get("class") == "segment":
            self.source_sections.append(self.in_details)
        if tag == "h2" and attrs.get("id") == "chapters-title":
            self.source_sections.append(self.in_details)
        if tag == "a":
            self.hrefs.append(attrs.get("href", ""))
        if tag == "script":
            self.scripts += 1

    def handle_endtag(self, tag):
        if tag == "details":
            self.in_details = False


class SummaryReaderTests(unittest.TestCase):
    def build(self, root, evidence, *, untimed=False, source="https://www.youtube.com/watch?v=example", extra=None, handoff=None, include_transcript=True, transcript_segments=None):
        segment = {"segment_id": 1, "speaker": "嘉宾", "text": "可靠评估让产品真正可用。"}
        if not untimed:
            segment.update(start="00:01:30", end="00:02:00", start_seconds=90, end_seconds=120)
        documents = {
            "bundle.json": {"source_input": source, "resolution": {"title": "原始节目标题"}, **(extra or {})},
            "transcript.json": {"segments": transcript_segments if transcript_segments is not None else [segment]},
            "evidence.json": evidence,
        }
        if handoff is not None:
            documents["analysis-handoff.json"] = handoff
        for name, document in documents.items():
            (root / name).write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        result = render(root, root / "reader.html", include_transcript=include_transcript)
        page = (root / "reader.html").read_text(encoding="utf-8")
        parsed = PageStructure()
        parsed.feed(page)
        return result, page, parsed

    def test_digest_is_primary_with_evidence_and_collapsed_source(self):
        evidence = {
            "summary": "旧摘要",
            "digest": {
                "headline": "AI 产品真正需要什么？",
                "takeaway": "先建立可靠评估，再扩大模型。",
                "evidence": [{"segment_ids": [1]}],
                "participants": [{"name": "测试嘉宾", "role": "研究员", "description": "分享实践"}],
                "quick_takes": [{"question": "先做什么？", "answer": "建立评估", "evidence": [{"segment_ids": [1]}]}],
                "insights": [{"title": "从失败样本开始", "kind": "method", "summary": "评估必须贴近真实任务。", "bullets": ["收集失败案例"], "evidence": [{"start": "00:01:30", "end": "00:02:00", "segment_ids": [1]}]}],
                "open_questions": ["评估如何覆盖未知场景？"],
            },
            "chapters": [{"title": "可靠评估", "start": "00:01:30", "end": "00:02:00"}],
        }
        with tempfile.TemporaryDirectory() as folder:
            result, page, parsed = self.build(Path(folder), evidence)
        self.assertEqual(result["quick_takes"], 1)
        self.assertEqual(result["insights"], 1)
        self.assertIn("<h1>AI 产品真正需要什么？</h1>", page)
        self.assertIn("先建立可靠评估，再扩大模型。", page)
        self.assertIn("收集失败案例", page)
        self.assertIn("方法步骤", page)
        self.assertIn("评估如何覆盖未知场景？", page)
        self.assertLess(page.index('id="quick-title"'), page.index('id="source-details"'))
        self.assertEqual(parsed.details_open, [False])
        self.assertEqual(parsed.source_sections, [True, True])
        self.assertTrue(any("t=90s" in url for url in parsed.hrefs))
        self.assertNotIn('id="actions-title"', page)
        self.assertNotIn('id="quotes-title"', page)

    def test_untimed_evidence_uses_segment_anchor_without_zero_timestamp(self):
        evidence = {"digest": {"quick_takes": [{"question": "问题", "answer": "答案", "evidence": [{"start": None, "end": None, "segment_ids": [1]}]}]}}
        with tempfile.TemporaryDirectory() as folder:
            result, page, parsed = self.build(Path(folder), evidence, untimed=True)
        self.assertFalse(result["timestamp_links"])
        self.assertIn("原文段落 1", page)
        self.assertIn("#segment-1", parsed.hrefs)
        self.assertNotIn("00:00:00", page)
        self.assertNotIn("t=0s", page)

    def test_inferred_ranges_are_chronological_even_when_ids_are_unsorted(self):
        evidence = {"digest": {"quick_takes": [{"question": "问题", "answer": "答案", "evidence": [{"segment_ids": [2, 1]}]}]}}
        segments = [
            {"segment_id": 1, "text": "First", "start_seconds": 30, "end_seconds": 60},
            {"segment_id": 2, "text": "Second", "start_seconds": 120, "end_seconds": 180},
        ]
        with tempfile.TemporaryDirectory() as folder:
            _, page, parsed = self.build(Path(folder), evidence, transcript_segments=segments, source="https://example.org/episode")
        self.assertIn("00:00:30–00:03:00", page)
        self.assertIn("#segment-1", parsed.hrefs)
        self.assertNotIn("#segment-2", parsed.hrefs)

    def test_mixed_untimed_references_do_not_get_an_invented_combined_range(self):
        evidence = {"digest": {"quick_takes": [{"question": "问题", "answer": "答案", "evidence": [{"segment_ids": [1, 2]}]}]}}
        segments = [
            {"segment_id": 1, "text": "First", "start_seconds": 30, "end_seconds": 60},
            {"segment_id": 2, "text": "Second"},
        ]
        with tempfile.TemporaryDirectory() as folder:
            _, page, _ = self.build(Path(folder), evidence, transcript_segments=segments, include_transcript=False)
        self.assertIn("原文段落 1, 2", page)
        self.assertNotIn("t=30s", page)

    def test_legacy_claims_and_summary_remain_useful(self):
        evidence = {"summary": "本期最重要的一件事。", "claims": [{"claim": "评估比参数规模更重要。", "evidence": [{"segment_ids": [1]}]}], "limitations": ["样本有限。"]}
        with tempfile.TemporaryDirectory() as folder:
            result, page, _ = self.build(Path(folder), evidence)
        self.assertEqual(result["insights"], 1)
        self.assertIn("本期最重要的一件事。", page)
        self.assertIn("评估比参数规模更重要。", page)
        self.assertIn("样本有限。", page)
        self.assertNotIn('id="participants-title"', page)

    def test_html_is_escaped_and_unsafe_source_urls_are_not_links(self):
        payload = '<script>alert("x")</script>'
        evidence = {"episode": {"source_url": "javascript:alert(1)"}, "digest": {"headline": payload, "takeaway": payload, "participants": [{"name": payload}], "quick_takes": [{"question": payload, "answer": payload, "evidence": [{"segment_ids": [1]}]}]}, "quotes": [{"text": payload, "segment_ids": [1]}]}
        with tempfile.TemporaryDirectory() as folder:
            result, page, parsed = self.build(Path(folder), evidence, source="data:text/html,<script>alert(1)</script>")
        self.assertEqual(parsed.scripts, 1)
        self.assertNotIn(payload, page)
        self.assertIn("&lt;script&gt;", page)
        self.assertFalse(result["timestamp_links"])
        self.assertFalse(any(url.startswith(("javascript:", "data:")) for url in parsed.hrefs))

    def test_english_labels_are_selected_from_bundle_or_handoff(self):
        for extra, handoff in [({"output_language": "en"}, None), ({"request": {"output_language": "en-US"}}, None), ({}, {"output_language": "English"})]:
            with self.subTest(extra=extra, handoff=handoff), tempfile.TemporaryDirectory() as folder:
                _, page, _ = self.build(Path(folder), {"summary": "A short summary."}, extra=extra, handoff=handoff)
            self.assertIn('<html lang="en">', page)
            self.assertIn("The takeaway", page)
            self.assertIn("Explore chapters &amp; transcript", page)
            self.assertNotIn("一句话看懂", page)

    def test_bundle_language_overrides_stale_evidence_and_search_preserves_unicode(self):
        with tempfile.TemporaryDirectory() as folder:
            _, page, _ = self.build(Path(folder), {"summary": "Summary", "output_language": "zh-CN"}, extra={"output_language": " en "}, transcript_segments=[{"segment_id": 1, "text": "Straße"}])
        self.assertIn('<html lang="en">', page)
        self.assertIn('data-search=" straße"', page)
        self.assertNotIn('data-search=" strasse"', page)

    def test_unknown_platform_keeps_original_link_without_fabricated_seek_url(self):
        with tempfile.TemporaryDirectory() as folder:
            result, _, parsed = self.build(Path(folder), {"claims": [{"claim": "观点", "evidence": [{"segment_ids": [1]}]}]}, source="https://podcast.example/episode")
        self.assertFalse(result["timestamp_links"])
        self.assertIn("https://podcast.example/episode", parsed.hrefs)
        self.assertIn("#segment-1", parsed.hrefs)
        self.assertFalse(any("#t=" in value for value in parsed.hrefs))

    def test_share_page_omits_transcript_content_search_script_and_dead_anchors(self):
        evidence = {"digest": {"headline": "分享摘要", "quick_takes": [{"question": "问题", "answer": "答案", "evidence": [{"segment_ids": [1]}]}]}, "chapters": [{"title": "介绍", "start": "00:01:30", "end": "00:02:00"}]}
        with tempfile.TemporaryDirectory() as folder:
            result, page, parsed = self.build(Path(folder), evidence, source="https://example.org/podcast", include_transcript=False)
        self.assertEqual(result["segments"], 0)
        self.assertNotIn("可靠评估让产品真正可用。", page)
        self.assertNotIn('id="transcript-title"', page)
        self.assertNotIn('id="search"', page)
        self.assertEqual(parsed.scripts, 0)
        self.assertFalse(any(value.startswith("#segment-") for value in parsed.hrefs))
        self.assertIn("展开节目章节", page)
        self.assertIn("分享摘要", page)

    def test_timestamp_urls_are_supported_and_strictly_validated(self):
        self.assertIn("t=90s", timestamp_url("https://www.youtube.com/watch?v=x&t=12&start=4", 90))
        self.assertNotIn("start=", timestamp_url("https://www.youtube.com/watch?v=x&start=4", 90))
        self.assertIn("t=90", timestamp_url("https://www.bilibili.com/video/BV1x", 90))
        for url in ("javascript:alert(1)", "file:///tmp/a", "https://evilyoutube.com/x", "https://youtube.com\\@evil.example/x", "https://user:password@youtube.com/watch", "https://youtube.com:bad/watch", "https://youtube.com/\n"):
            with self.subTest(url=url):
                self.assertIsNone(timestamp_url(url, 90))
        for value in (None, "not a time", "1e308:00:00", float("nan"), float("inf"), -10):
            with self.subTest(value=value):
                self.assertIsNone(timestamp_url("https://youtube.com/watch?v=x", value))


if __name__ == "__main__":
    unittest.main()
