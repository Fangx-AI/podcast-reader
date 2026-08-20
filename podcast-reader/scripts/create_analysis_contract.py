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
        "required_outputs": {"analysis": "analysis.md", "evidence": "evidence.json"},
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
    output = episode_dir / "analysis-handoff.json"
    atomic_write_json(output, contract)
    bundle_path = episode_dir / "bundle.json"
    bundle = load_json_object(bundle_path) or {}
    bundle["analysis_handoff"] = "analysis-handoff.json"
    bundle["next_actions"] = [
        "current Agent: complete analysis.md and evidence.json using analysis-handoff.json",
        "run finalize_bundle.py and validate_bundle.py before reporting analysis complete",
    ]
    atomic_write_json(bundle_path, bundle)
    return contract


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode_dir")
    parser.add_argument("--mode", choices=tuple(MODES), default="standard")
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
