import copy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from summary_digest import render_markdown, validate_digest


class SummaryDigestTests(unittest.TestCase):
    def setUp(self):
        self.transcript = {
            "segments": [
                {"segment_id": 1, "start_seconds": 0, "end_seconds": 10, "text": "Small experiments reveal useful evidence."},
                {"segment_id": 2, "start_seconds": 10, "end_seconds": 20, "text": "Measure outcomes before investing further."},
                {"segment_id": 3, "start_seconds": 100, "end_seconds": 120, "text": "Later discussion."},
            ]
        }
        reference = {"start": "00:00:00", "end": "00:00:10", "segment_ids": [1]}
        self.evidence = {
            "schema_version": "2.0",
            "episode": {"title": "一次小实验", "show": "示例播客", "source_url": "https://example.com/episode"},
            "digest": {
                "headline": "先小步验证，再决定投入",
                "takeaway": "本期主张用小实验检验判断，依据结果决定是否继续投入。",
                "evidence": [copy.deepcopy(reference)],
                "participants": [{"name": "主持人", "role": None, "description": None}],
                "quick_takes": [{"question": "如何开始？", "answer": "先设计一个小实验。", "evidence": [copy.deepcopy(reference)]}],
                "insights": [{"title": "先验证判断", "summary": "小实验能让判断接受事实检验。", "bullets": ["定义需要观察的结果。"], "evidence": [copy.deepcopy(reference)]}],
            },
            "quotes": [],
            "actions": [],
            "chapters": [],
            "limitations": ["仅依据本期材料整理。"],
        }

    def test_valid_digest_and_markdown_sections(self):
        result = validate_digest(self.evidence, self.transcript, required=True)
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["metrics"]["cited_segments"], 1)
        markdown = render_markdown(self.evidence, {}, self.transcript)
        for value in ("# 先小步验证", "## 一句话总结", "## 关键问题 · 直接看答案", "## 高价值信息", "## 说明与限制", "[00:00:00–00:00:10]"):
            self.assertIn(value, markdown)
        self.assertNotIn("## 回听章节", markdown)
        self.assertNotIn("## 可以怎么做", markdown)

    def test_absent_digest_is_legacy_compatible_but_null_is_invalid(self):
        self.assertTrue(validate_digest({}, self.transcript)["valid"])
        self.assertFalse(validate_digest({}, self.transcript, required=True)["valid"])
        self.assertFalse(validate_digest({"digest": None}, self.transcript)["valid"])
        self.assertFalse(validate_digest([], self.transcript)["valid"])

    def test_required_content_and_collection_schema(self):
        cases = [
            ("headline", None), ("headline", 42), ("headline", ""),
            ("takeaway", "TODO"), ("evidence", []), ("evidence", {}),
            ("quick_takes", []), ("quick_takes", "text"), ("quick_takes", [None]),
            ("insights", [None]), ("insights", []), ("participants", ["name"]),
            ("participants", [{"name": []}]), ("unexpected_field", "value"),
        ]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                document = copy.deepcopy(self.evidence)
                document["digest"][key] = value
                self.assertFalse(validate_digest(document, self.transcript)["valid"])

    def test_optional_null_and_absent_fields(self):
        for remove in (False, True):
            document = copy.deepcopy(self.evidence)
            if remove:
                document["digest"].pop("participants")
                document["digest"]["insights"][0].pop("bullets")
            else:
                document["digest"]["participants"] = None
                document["digest"]["insights"][0]["bullets"] = None
            self.assertTrue(validate_digest(document, self.transcript)["valid"])
            self.assertNotIn("## 本期人物", render_markdown(document, {}, self.transcript))

    def test_reference_membership_and_boolean_ids_are_checked(self):
        for ids in ([999], [True], [1.0], ["1"], [], [1, 1], [-1]):
            with self.subTest(ids=ids):
                document = copy.deepcopy(self.evidence)
                document["digest"]["quick_takes"][0]["evidence"][0]["segment_ids"] = ids
                self.assertFalse(validate_digest(document, self.transcript)["valid"])

    def test_nonfinite_incomplete_and_invalid_clock_references_fail(self):
        for start, end in [
            (float("nan"), 10), (0, float("inf")), (False, 10), (0, True),
            ("00:00:00", None), (None, 10), ("00:99:00", 10), (-1, 10),
            (10, 0), (0, 1000), (0, "NaN"), (0, 10**400),
        ]:
            with self.subTest(start=start, end=end):
                document = copy.deepcopy(self.evidence)
                document["digest"]["evidence"][0].update(start=start, end=end)
                self.assertFalse(validate_digest(document, self.transcript)["valid"])

    def test_wide_forged_reference_cannot_hide_behind_one_overlapping_segment(self):
        for reference in [
            {"start": 0, "end": 120, "segment_ids": [1]},
            {"start": 100, "end": 120, "segment_ids": [1, 3]},
            {"start": 50, "end": 60, "segment_ids": [1, 3]},
        ]:
            document = copy.deepcopy(self.evidence)
            document["digest"]["insights"][0]["evidence"] = [reference]
            self.assertFalse(validate_digest(document, self.transcript)["valid"])

    def test_untimed_text_uses_segment_citations_without_fabricated_clocks(self):
        transcript = {"segments": [{"segment_id": 1, "text": "Some source text", "start_seconds": None, "end_seconds": None}]}
        document = copy.deepcopy(self.evidence)
        for item in [document["digest"], *document["digest"]["quick_takes"], *document["digest"]["insights"]]:
            item["evidence"] = [{"segment_ids": [1], "start": None, "end": None}]
        result = validate_digest(document, transcript, required=True)
        self.assertTrue(result["valid"], result)
        markdown = render_markdown(document, {}, transcript)
        self.assertIn("文本段 #1", markdown)
        self.assertNotIn("00:00", markdown)
        self.assertNotIn("回听章节", markdown)
        document["digest"]["evidence"][0].update(start=0, end=0)
        self.assertFalse(validate_digest(document, transcript)["valid"])

    def test_malformed_source_times_do_not_crash_reference_validation(self):
        for invalid in ("invalid", float("nan"), True, [], {}):
            transcript = copy.deepcopy(self.transcript)
            transcript["segments"][0]["start_seconds"] = invalid
            self.assertFalse(validate_digest(self.evidence, transcript)["valid"])

    def test_ids_only_references_derive_real_timestamps(self):
        document = copy.deepcopy(self.evidence)
        document["digest"]["evidence"] = [{"segment_ids": [1, 2]}]
        self.assertTrue(validate_digest(document, self.transcript)["valid"])
        self.assertIn("[00:00:00–00:00:20]", render_markdown(document, {}, self.transcript))

    def test_quotes_actions_and_limitations_are_bounded_and_typed(self):
        cases = [
            ("quotes", [{"text": "Exact", "segment_ids": [1]}] * 4),
            ("quotes", [{"text": "Exact", "segment_ids": [True]}]),
            ("actions", [{"action": "Try it", "evidence": []}]),
            ("limitations", [{"text": "not a string"}]),
            ("limitations", ["{{fill me}}"]),
            ("chapters", [{"start": 0, "end": float("nan"), "title": "An invalid chapter"}]),
        ]
        for key, value in cases:
            with self.subTest(key=key):
                document = copy.deepcopy(self.evidence)
                document[key] = value
                self.assertFalse(validate_digest(document, self.transcript)["valid"])

    def test_individual_and_overall_brevity_limits(self):
        document = copy.deepcopy(self.evidence)
        document["digest"]["quick_takes"][0]["answer"] = "字" * 501
        self.assertFalse(validate_digest(document, self.transcript)["valid"])
        document = copy.deepcopy(self.evidence)
        insight = copy.deepcopy(document["digest"]["insights"][0])
        insight["summary"] = "字" * 700
        insight["bullets"] = ["字" * 300] * 4
        document["digest"]["insights"] = [copy.deepcopy(insight) for _ in range(7)]
        result = validate_digest(document, self.transcript)
        self.assertFalse(result["valid"])
        self.assertTrue(any("concise-summary budget" in error for error in result["errors"]))

    def test_markdown_escapes_untrusted_content_and_rejects_active_source_urls(self):
        document = copy.deepcopy(self.evidence)
        attack = '<script>alert(1)</script> [click](javascript:alert(1))\n# injected'
        document["digest"]["headline"] = attack
        document["digest"]["participants"][0]["name"] = "**Fake bold**"
        document["episode"]["title"] = '<img src=x onerror="alert(1)">'
        document["episode"]["source_url"] = "javascript:alert(1)"
        markdown = render_markdown(document, {}, self.transcript)
        self.assertNotIn("<script>", markdown)
        self.assertNotIn("<img", markdown)
        self.assertNotIn("[click](javascript:", markdown)
        self.assertNotIn("\n# injected", markdown)
        self.assertNotIn("[收听原节目]", markdown)
        self.assertIn("&lt;script&gt;", markdown)
        self.assertIn(r"\*\*Fake bold\*\*", markdown)
        document["episode"]["source_url"] = "https://example.com/path?q=1)> <script>"
        markdown = render_markdown(document, {}, self.transcript)
        self.assertIn("%29%3E%20%3Cscript%3E", markdown)
        self.assertNotIn("<script>", markdown)

    def test_renderer_rejects_invalid_digest_instead_of_silently_filling_it(self):
        document = copy.deepcopy(self.evidence)
        document["digest"]["takeaway"] = ""
        with self.assertRaisesRegex(ValueError, "invalid digest"):
            render_markdown(document, {}, self.transcript)

    def test_optional_open_questions_and_insight_kinds(self):
        document = copy.deepcopy(self.evidence)
        document["digest"]["open_questions"] = ["实验结束后，如何决定下一步？"]
        document["digest"]["insights"][0]["kind"] = "method"
        self.assertTrue(validate_digest(document, self.transcript)["valid"])
        markdown = render_markdown(document, {}, self.transcript)
        self.assertIn("## 仍未解决的问题", markdown)
        self.assertIn("具体方法", markdown)
        for invalid in ("unknown", [], 123):
            document["digest"]["insights"][0]["kind"] = invalid
            self.assertFalse(validate_digest(document, self.transcript)["valid"])
        document["digest"]["insights"][0]["kind"] = None
        document["digest"]["open_questions"] = None
        self.assertTrue(validate_digest(document, self.transcript)["valid"])
        for invalid in (["Q"] * 6, ["Q" * 301], [None], "Question"):
            document["digest"]["open_questions"] = invalid
            self.assertFalse(validate_digest(document, self.transcript)["valid"])

    def test_english_output_localizes_headings_metadata_and_untimed_citations(self):
        document = copy.deepcopy(self.evidence)
        transcript = {"segments": [{"segment_id": 1, "text": "Source text"}]}
        for item in [document["digest"], *document["digest"]["quick_takes"], *document["digest"]["insights"]]:
            item["evidence"] = [{"segment_ids": [1]}]
        document["digest"]["insights"][0]["kind"] = "method"
        document["digest"]["open_questions"] = ["What remains uncertain?"]
        markdown = render_markdown(document, {"output_language": "en"}, transcript)
        for expected in ("Source:", "Listen to the episode", "## One-sentence takeaway",
                         "## Key questions · Direct answers", "## High-value insights",
                         "## Participants", "Text segment #1", " · Method",
                         "## Open questions", "## Notes and limitations"):
            self.assertIn(expected, markdown)
        for forbidden in ("来源：", "文本段", "## 一句话总结", "## 高价值信息"):
            self.assertNotIn(forbidden, markdown)

    def test_local_source_displays_only_basename_even_without_episode_metadata(self):
        document = copy.deepcopy(self.evidence)
        document.pop("episode")
        for source in (r"C:\private\podcasts\episode.txt", "/private/podcasts/episode.txt"):
            for language in ("zh-CN", "en"):
                with self.subTest(source=source, language=language):
                    markdown = render_markdown(document, {"source_input": source, "output_language": language}, self.transcript)
                    label = "Local text" if language == "en" else "本地文本"
                    self.assertIn(label + r" · episode\.txt", markdown)
                    self.assertNotIn("private", markdown)
                    self.assertNotIn("podcasts", markdown)
                    self.assertNotIn(source, markdown)


if __name__ == "__main__":
    unittest.main()
