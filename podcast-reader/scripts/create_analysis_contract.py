#!/usr/bin/env python3
"""Create a provider-neutral Agent handoff for completing podcast analysis."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from runtime_utils import atomic_write_json, load_json_object, skill_version


MODES = {
    "summary": ["core question", "ranked key questions with origins, stakes and answer coverage", "one-sentence takeaway", "high-value insights supporting those questions", "participants when known", "short exact quotes when useful", "source references", "limitations"],
    "quick": ["episode card", "short summary", "key moments", "limitations"],
    "standard": ["episode card", "executive summary", "chapters", "key ideas", "claims", "actions", "limitations"],
    "deep": ["standard outputs", "argument map", "counterarguments", "claim ledger", "entities", "verification queue", "research questions"],
}


def create(episode_dir: Path, mode: str, output_language: str) -> dict:
    episode_dir = episode_dir.expanduser().resolve()
    required = [episode_dir / "bundle.json", episode_dir / "transcript.json", episode_dir / "chunks.json"]
    missing = [path.name for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("analysis handoff requires: " + ", ".join(missing))
    contract = {
        "schema_version": "2.0",
        "skill_version": skill_version(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "awaiting_agent_analysis",
        "mode": mode,
        "output_language": output_language,
        "inputs": {"bundle": "bundle.json", "transcript": "transcript.json", "index": "chunks.json", "visual_manifest": "frames/manifest.json" if (episode_dir / "frames" / "manifest.json").is_file() else None},
        "required_outputs": {"evidence": "evidence.json"} if mode == "summary" else {"analysis": "analysis.md", "evidence": "evidence.json"},
        "optional_outputs": {"summary": "summary.md", "translations": "translations/", "reader": "reader.html"},
        "content_requirements": MODES[mode],
        "evidence_contract": {
            "material_claims_require_segment_ids": True,
            "quotes_must_be_exact_transcript_substrings": True,
            "timestamps_must_be_within_transcript_duration": True,
            "source_content_and_agent_synthesis_must_be_labeled": True,
        },
        "completion_gate": [
            "python scripts/finalize_bundle.py <episode_dir>",
            "python scripts/validate_bundle.py <episode_dir>",
        ],
        "agent_instruction": "Continue in the current Agent: retrieve relevant chunks, write analysis.md and evidence.json in the requested language, validate them, and do not report completion while bundle status is ready_for_analysis.",
    }
    if mode == "summary":
        contract.update({
            "generated_outputs": {"summary": "summary.md", "reader": "reader.html", "analysis_compatibility": "analysis.md"},
            "optional_outputs": {},
            "summary_contract": {
                "schema_reference": "references/output-schema.md",
                "question_contract_version": 1,
                "required_digest_fields": ["headline", "core_question", "takeaway", "evidence", "quick_takes", "insights"],
                "required_quick_take_fields": ["question", "why_it_matters", "question_origin", "answer_status", "answer", "evidence"],
                "reading_target": "For substantial episodes, aim for 3–5 minutes and roughly 900–1600 Chinese characters or 500–900 English words across the visible summary. These are editorial targets, not minimums or validation limits. Short episodes should be shorter; the renderer estimates reading time from actual text.",
                "question_workflow": "Read the complete material, write the episode's core_question, collect candidate questions, distinguish explicitly asked questions from synthesized ones, rank by effect on understanding or decisions, information value and genuinely unresolved issues, merge duplicates, then verify the scope of each answer against the full source.",
                "core_question": "Required for new summaries: one specific, source-grounded question that explains what the episode is trying to resolve. Do not merely reuse a broad topic label or turn the takeaway into a vague question.",
                "first_30_seconds": "Show each question immediately followed by its short answer and most valuable details. Do not create a bare question index that requires a jump to find the answers. Keep the question's subject, conflict and conditions intact, and show incomplete answers directly in the card.",
                "quick_takes": "1–6 concrete questions that remain understandable in isolation, one main problem each. Generic questions such as 'Where to start?' or 'What are the lessons?' are unacceptable. Include why_it_matters, question_origin, answer_status, answer and evidence for each. Lead answers with the episode's actual response, preserve decisive caveats, and explicitly describe missing answers rather than inventing them. Chinese answers may often fit in 30–60 characters, but specificity and source fidelity take priority.",
                "why_it_matters": "Explain the source-supported stakes of this question in a concise sentence: what understanding, judgment, boundary or unresolved issue depends on it. Do not invent audience motives, benefits, harms or stakes.",
                "key_points": "For each newly authored question, add 1–3 concise strings with the most valuable source-backed details: concrete examples, mechanisms, distinctions, methods or conditions. Place them directly below the short answer and support them with the same card's evidence, adding references where necessary. Do not repeat the answer, pad sparse material or invent details. This field remains optional for legacy compatibility.",
                "question_origin": "Use explicit when the source clearly asks this question, including a faithful rephrasing; use synthesized when the Agent derives a useful question from the discussion. A synthesized question must not be presented as a speaker's original words.",
                "answer_status": "Use answered when the episode addresses the actual scope of the question, partial when it answers only part, and unanswered when it offers no answer. This describes episode answer coverage, not factual verification, correctness or confidence. Do not force an unanswered card merely to display every status.",
                "gap": "Required nonempty gap for partial or unanswered: state exactly what the episode leaves unresolved, without adding an unrelated research agenda. Omit gap for answered questions.",
                "question_evidence": "References must support the question's origin and stakes, the response and its coverage, including distant follow-ups or explicit unresolved passages. Cite the passages from which a synthesized question is derived.",
                "insights": "1–7 additional insights beyond the question cards. Put question-specific examples, mechanisms and conditions in that question's key_points first. Omit details that repeat a card. Rank the remaining insights by value, retain attribution and put decisive caveats beside the affected claim.",
                "insight_kinds": ["decision", "counterintuitive", "data", "method", "pitfall", "insight"],
                "open_questions": "Legacy optional field only. For new summaries, represent important incomplete or missing answers within quick_takes using answer_status and gap. Do not repeat the same question in open_questions.",
                "participants": "Include only names, roles and context established by source metadata or transcript; omit unknown identities",
                "quotes": "0–3 short exact source quotes; omit when unnecessary or untimed",
                "actions": "Optional, only when supported and useful for this episode's genre",
                "whole_episode": "Read the complete chunk index in chronological batches before synthesis; cover beginning, middle and ending, then retrieve detail. A top-k search alone cannot summarize an entire episode.",
                "untimed_sources": "Use segment_ids without timestamps; never invent timing, duration, or speaker identities",
                "no_padding": "Omit empty or redundant optional sections. Keep participant context, quotes, actions and open questions only when each adds something useful. Do not produce a research report, claim ledger, translation or argument map by default.",
                "selection_test": "Read each question without the title or neighboring cards: are its subject, tension and scope still clear? Compare candidates by decision impact, information value and actual unresolved gaps, merge overlapping questions, then check every answer against the question's full scope. Remove duplicated insights and preserve meaningful uncertainty.",
            },
            "agent_instruction": "Continue in the current Agent: inspect all transcript chunks, identify the core question, collect and rank explicit/synthesized candidate questions, merge duplicates, and verify answer coverage before writing evidence.json. Put a direct short answer and source-backed key_points immediately under each question. Every new question card requires why_it_matters, question_origin, answer_status and evidence; partial/unanswered cards require gap. Add only supplementary insights that do not repeat a card. Use references/output-schema.md. Run finalize_bundle.py to generate summary.md and reader.html, then validate_bundle.py. Deliver those two files. Transcript acquisition or ready_for_analysis is not a finished summary.",
        })
    output = episode_dir / "analysis-handoff.json"
    atomic_write_json(output, contract)
    bundle_path = episode_dir / "bundle.json"
    bundle = load_json_object(bundle_path) or {}
    bundle["analysis_handoff"] = "analysis-handoff.json"
    bundle["analysis_mode"] = mode
    bundle["output_language"] = output_language
    if mode == "summary":
        bundle["question_contract_version"] = 1
    else:
        bundle.pop("question_contract_version", None)
    bundle["status"] = "ready_for_analysis"
    bundle.pop("completed_at", None)
    bundle["next_actions"] = [
        "current Agent: complete evidence.json with digest using analysis-handoff.json" if mode == "summary" else "current Agent: complete analysis.md and evidence.json using analysis-handoff.json",
        "run finalize_bundle.py and validate_bundle.py before reporting analysis complete",
    ]
    atomic_write_json(bundle_path, bundle)
    return contract


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode_dir")
    parser.add_argument("--mode", choices=tuple(MODES), default="summary")
    parser.add_argument("--output-language", default="user-language")
    args = parser.parse_args()
    try:
        contract = create(Path(args.episode_dir), args.mode, args.output_language)
        print(json.dumps({"status": "ready", "handoff": str(Path(args.episode_dir).expanduser().resolve() / "analysis-handoff.json"), "contract": contract}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
