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

    def question_first_document(self, status="answered"):
        document = copy.deepcopy(self.evidence)
        document["digest"]["core_question"] = "怎样用小实验决定是否继续投入？"
        question = document["digest"]["quick_takes"][0]
        question.update({
            "why_it_matters": "起点决定了实验结果能否支持下一步决策。",
            "question_origin": "synthesized",
            "answer_status": status,
        })
        if status in {"partial", "unanswered"}:
            question["gap"] = "节目没有给出继续投入的统一门槛。"
        return document

    def test_question_first_contract_and_markdown_reading_order(self):
        document = self.question_first_document("partial")
        document["digest"]["quick_takes"][0]["key_points"] = ["用可观察的结果判断下一步投入。"]
        result = validate_digest(document, self.transcript, required=True)
        self.assertTrue(result["valid"], result)
        markdown = render_markdown(document, {}, self.transcript)
        sections = ["# 先小步验证", "## 本期核心问题", "## 一句话总结", "## 关键问题 · 直接看答案", "## 补充洞察"]
        positions = [markdown.index(section) for section in sections]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("### 1. 如何开始？\n\n**省流答案（部分回答）：** 先设计一个小实验。", markdown)
        card = markdown.split("### 1. 如何开始？", 1)[1].split("## 补充洞察", 1)[0]
        fields = ["**省流答案", "**最有价值的信息", "- 用可观察的结果", "**仍缺什么", "**为什么重要", "问题来源：", "原文出处："]
        positions = [card.index(field) for field in fields]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(markdown.count("如何开始？"), 1)
        self.assertIn("**为什么重要：**", markdown)
        self.assertIn("**仍缺什么：**", markdown)
        self.assertIn("问题来源：根据节目讨论归纳", markdown)
        self.assertIn("原文出处：[00:00:00–00:00:10]", markdown)

    def test_legacy_questions_do_not_receive_invented_core_question_or_status(self):
        self.assertTrue(validate_digest(self.evidence, self.transcript)["valid"])
        markdown = render_markdown(self.evidence, {}, self.transcript)
        self.assertIn("### 1. 如何开始？\n\n**省流答案：** 先设计一个小实验。", markdown)
        for absent in ("## 本期核心问题", "节目回答状态", "已回答", "为什么重要", "问题来源："):
            self.assertNotIn(absent, markdown)
        self.assertNotIn("最有价值的信息", markdown)

    def test_core_question_and_new_fields_are_typed_bounded_and_required(self):
        for invalid in (None, "", " ", [], "问" * 161):
            document = self.question_first_document()
            document["digest"]["core_question"] = invalid
            self.assertFalse(validate_digest(document, self.transcript)["valid"])
        for field in ("why_it_matters", "question_origin", "answer_status"):
            document = self.question_first_document()
            document["digest"]["quick_takes"][0].pop(field)
            self.assertFalse(validate_digest(document, self.transcript)["valid"], field)
        for field, invalid in (
            ("why_it_matters", ""), ("why_it_matters", "字" * 301),
            ("why_it_matters", []), ("question_origin", "inferred"),
            ("question_origin", None), ("question_origin", []),
            ("answer_status", "verified"), ("answer_status", None),
            ("answer_status", []), ("gap", 123),
        ):
            document = self.question_first_document()
            document["digest"]["quick_takes"][0][field] = invalid
            self.assertFalse(validate_digest(document, self.transcript)["valid"], (field, invalid))

    def test_answer_status_and_gap_are_consistent_even_without_core_question(self):
        for status in ("partial", "unanswered"):
            for legacy in (False, True):
                document = self.question_first_document(status)
                if legacy:
                    document["digest"].pop("core_question")
                self.assertTrue(validate_digest(document, self.transcript)["valid"])
                for invalid in (None, "", " ", [], "字" * 301):
                    candidate = copy.deepcopy(document)
                    candidate["digest"]["quick_takes"][0]["gap"] = invalid
                    self.assertFalse(validate_digest(candidate, self.transcript)["valid"])
                document["digest"]["quick_takes"][0].pop("gap")
                self.assertFalse(validate_digest(document, self.transcript)["valid"])
        for gap in (None, "", " "):
            document = self.question_first_document("answered")
            document["digest"]["quick_takes"][0]["gap"] = gap
            self.assertTrue(validate_digest(document, self.transcript)["valid"])
        document["digest"]["quick_takes"][0]["gap"] = "Still missing evidence."
        self.assertFalse(validate_digest(document, self.transcript)["valid"])

    def test_duplicate_questions_ignore_only_case_whitespace_and_punctuation(self):
        for first, second in (("如何开始？", " 如 何 开 始! "), ("What matters?", "WHAT   MATTERS!"), ("怎么选——任务？", "怎么选任务")):
            document = copy.deepcopy(self.evidence)
            question = document["digest"]["quick_takes"][0]
            question["question"] = first
            duplicate = copy.deepcopy(question)
            duplicate["question"] = second
            document["digest"]["quick_takes"].append(duplicate)
            result = validate_digest(document, self.transcript)
            self.assertFalse(result["valid"])
            self.assertTrue(any("duplicates quick_takes" in error for error in result["errors"]))
        document["digest"]["quick_takes"][0]["question"] = "何时开始"
        document["digest"]["quick_takes"][1]["question"] = "什么时候开始"
        self.assertTrue(validate_digest(document, self.transcript)["valid"])

    def test_question_first_english_and_new_text_fields_are_safely_rendered(self):
        document = self.question_first_document("unanswered")
        attack = '<script>alert(1)</script> [link](javascript:alert(1))'
        document["digest"]["core_question"] = attack
        question = document["digest"]["quick_takes"][0]
        question["why_it_matters"] = attack
        question["gap"] = attack
        question["key_points"] = [attack]
        markdown = render_markdown(document, {"output_language": "en"}, self.transcript)
        for value in ("## The episode's core question", "**Most valuable details:**", "**Why it matters:**",
                      "**Short answer (Unanswered):**", "**What remains missing:**",
                      "Question origin: Synthesized from the episode's discussion", "Source evidence:"):
            self.assertIn(value, markdown)
        self.assertNotIn("<script>", markdown)
        self.assertNotIn("[link](javascript:", markdown)
        self.assertNotIn("节目回答状态", markdown)
        self.assertLess(markdown.index("**Short answer"), markdown.index("**Most valuable details"))

    def test_key_points_are_optional_but_supplied_values_are_bounded_and_typed(self):
        self.assertTrue(validate_digest(self.evidence, self.transcript)["valid"])
        for points in (["一个具体例子。"], ["字" * 300] * 3):
            document = self.question_first_document()
            document["digest"]["quick_takes"][0]["key_points"] = points
            self.assertTrue(validate_digest(document, self.transcript)["valid"])
        for points in (None, [], "一个具体例子。", {}, [None], [""], [" "], ["字" * 301], ["要点"] * 4, ["TODO"]):
            with self.subTest(points=points):
                document = copy.deepcopy(self.evidence)
                document["digest"]["quick_takes"][0]["key_points"] = points
                result = validate_digest(document, self.transcript)
                self.assertFalse(result["valid"])
                self.assertTrue(any("key_points" in error for error in result["errors"]))

    def test_key_points_count_toward_the_summary_text_budget(self):
        document = self.question_first_document()
        before = validate_digest(document, self.transcript)["metrics"]["text_characters"]
        document["digest"]["quick_takes"][0]["key_points"] = ["具体例子", "关键条件"]
        after = validate_digest(document, self.transcript)["metrics"]["text_characters"]
        self.assertEqual(after - before, 8)

    def test_core_question_cannot_bypass_source_reference_checks(self):
        document = self.question_first_document()
        document["digest"]["evidence"] = [{"segment_ids": [999]}]
        self.assertFalse(validate_digest(document, self.transcript)["valid"])

    def test_new_handoff_can_require_question_contract_without_breaking_legacy(self):
        self.assertTrue(validate_digest(self.evidence, self.transcript)["valid"])
        result = validate_digest(self.evidence, self.transcript, require_questions=True)
        self.assertFalse(result["valid"])
        self.assertTrue(any("digest.core_question" in error for error in result["errors"]))
        self.assertTrue(any("why_it_matters" in error for error in result["errors"]))
        self.assertFalse(validate_digest({}, self.transcript, require_questions=True)["valid"])
        self.assertTrue(validate_digest(self.question_first_document(), self.transcript, require_questions=True)["valid"])


if __name__ == "__main__":
    unittest.main()
