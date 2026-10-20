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
    "summary": ["one-sentence takeaway", "participants when known", "key questions and direct answers", "high-value insights", "unresolved questions when present", "short exact quotes when useful", "source references", "limitations"],
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
                "required_digest_fields": ["headline", "takeaway", "evidence", "quick_takes", "insights"],
                "reading_target": "3–5 minutes; use fewer points for short or simple episodes",
                "quick_takes": "1–6 questions the audience actually needs answered, each with a direct answer and the key reason, evidence or boundary. Identify the episode's central problem; avoid table-of-contents questions.",
                "insights": "1–7 high-value ideas selected for changed understanding or decisions: counterintuitive claims, meaningful data/examples, usable methods, tradeoffs, pitfalls and limits. Explain why each matters and preserve source attribution. Never pad with generic themes.",
                "insight_kinds": ["decision", "counterintuitive", "data", "method", "pitfall", "insight"],
                "open_questions": "Optional 0–5 questions the episode raises but does not resolve; distinguish missing answers from your own speculation. Omit if none.",
                "participants": "Include only names, roles and context established by source metadata or transcript; omit unknown identities",
                "quotes": "0–3 short exact source quotes; omit when unnecessary or untimed",
                "actions": "Optional, only when supported and useful for this episode's genre",
                "whole_episode": "Read the complete chunk index in chronological batches before synthesis; cover beginning, middle and ending, then retrieve detail. A top-k search alone cannot summarize an entire episode.",
                "untimed_sources": "Use segment_ids without timestamps; never invent timing, duration, or speaker identities",
                "no_padding": "Omit empty optional sections. Do not produce a research report, claim ledger, translation or argument map by default.",
                "selection_test": "Would a listener lose an important answer, surprising insight, concrete example or decision boundary if this item were removed? If not, merge or drop it. Preserve qualifications, disagreement and unanswered questions rather than manufacturing certainty.",
            },
            "agent_instruction": "Continue in the current Agent: inspect all transcript chunks, then write evidence.json with a concise, grounded digest in the requested language. Use references/output-schema.md. Run finalize_bundle.py to generate summary.md and reader.html, then validate_bundle.py. Deliver those two files. Transcript acquisition or ready_for_analysis is not a finished summary.",
        })
    output = episode_dir / "analysis-handoff.json"
    atomic_write_json(output, contract)
    bundle_path = episode_dir / "bundle.json"
    bundle = load_json_object(bundle_path) or {}
    bundle["analysis_handoff"] = "analysis-handoff.json"
    bundle["analysis_mode"] = mode
    bundle["output_language"] = output_language
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
