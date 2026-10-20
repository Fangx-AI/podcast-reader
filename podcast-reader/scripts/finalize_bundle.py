#!/usr/bin/env python3
"""Validate generated analysis artifacts and mark an episode bundle analyzed."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from prepare_episode import artifact_inventory
from validate_notes import validate as validate_notes
from runtime_utils import atomic_write_json, atomic_write_text, sha256_file
from evidence_validator import validate_evidence
from render_reader import render as render_reader
from summary_digest import render_markdown, validate_digest


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def evidence_segment_ids(value: Any) -> set[int]:
    found: set[int] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "segment_ids" and isinstance(child, list):
                found.update(item for item in child if isinstance(item, int))
            else:
                found.update(evidence_segment_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(evidence_segment_ids(child))
    return found


def finalize(episode_dir: Path) -> dict[str, Any]:
    episode_dir = episode_dir.expanduser().resolve()
    bundle_path = episode_dir / "bundle.json"
    transcript_path = episode_dir / "transcript.json"
    analysis_path = episode_dir / "analysis.md"
    summary_path = episode_dir / "summary.md"
    evidence_path = episode_dir / "evidence.json"

    checks = {
        "bundle_exists": bundle_path.is_file(),
        "transcript_exists": transcript_path.is_file(),
        "evidence_exists": evidence_path.is_file(),
    }
    if not all(checks.values()):
        missing = [name for name, passed in checks.items() if not passed]
        return {"episode_dir": str(episode_dir), "checks": checks, "errors": missing, "valid": False}

    bundle = load_json(bundle_path)
    transcript = load_json(transcript_path)
    errors: list[str] = []
    evidence: dict[str, Any] = {}

    if evidence_path.is_file():
        try:
            evidence = load_json(evidence_path)
            evidence_result = validate_evidence(evidence, transcript)
            checks["evidence_json"] = isinstance(evidence, dict) and evidence.get("schema_version") in {"1.0", "2.0"}
            checks["evidence_references"] = bool(evidence_result["valid"])
            checks["evidence_quotes_exact"] = not any("quote text" in item for item in evidence_result["errors"])
            if not evidence_result["valid"]:
                errors.extend(f"evidence:{item}" for item in evidence_result["errors"])
            bundle["quality_metrics"] = evidence_result.get("metrics", {})
        except (OSError, ValueError, TypeError) as exc:
            checks["evidence_json"] = False
            checks["evidence_references"] = False
            errors.append(f"evidence:{exc}")

    summary_mode = bundle.get("analysis_mode") == "summary" or (
        not bundle.get("analysis_mode") and isinstance(evidence, dict) and "digest" in evidence
    )
    if summary_mode:
        digest_result = validate_digest(evidence, transcript, required=True)
        checks["summary_grounded"] = digest_result["valid"]
        errors.extend(f"summary:{item}" for item in digest_result["errors"])
    else:
        checks["analysis_exists"] = analysis_path.is_file()
        if not analysis_path.is_file():
            errors.append("analysis_exists")
        else:
            analysis_result = validate_notes(analysis_path, strict=True, transcript_path=transcript_path)
            checks["analysis_strict"] = bool(analysis_result["valid"])
            errors.extend(f"analysis:{failure}" for failure in analysis_result["failures"])
        if summary_path.is_file():
            summary_result = validate_notes(summary_path, strict=True, transcript_path=transcript_path)
            checks["summary_strict"] = bool(summary_result["valid"])
            errors.extend(f"summary:{failure}" for failure in summary_result["failures"])

    if errors:
        return {"episode_dir": str(episode_dir), "checks": checks, "errors": errors, "valid": False}

    if summary_mode:
        # One validated source of content keeps the two deliverables consistent.
        markdown = render_markdown(evidence, bundle, transcript)
        atomic_write_text(summary_path, markdown)
        atomic_write_text(analysis_path, markdown)
        checks["summary_written"] = True

    try:
        reader_result = render_reader(episode_dir, episode_dir / "reader.html")
        checks["reader_rendered"] = reader_result.get("status") == "rendered"
    except Exception as exc:
        checks["reader_rendered"] = False
        return {"episode_dir": str(episode_dir), "checks": checks, "errors": [f"reader:{exc}"], "valid": False}

    bundle["status"] = "analyzed"
    bundle["updated_at"] = datetime.now(timezone.utc).isoformat()
    bundle["completed_at"] = bundle["updated_at"]
    bundle["artifacts"] = artifact_inventory(episode_dir)
    if summary_mode:
        bundle["analysis_mode"] = "summary"
        bundle["deliverables"] = {"summary": "summary.md", "reader": "reader.html"}
        bundle["deliverable_hashes"] = {
            name: sha256_file(episode_dir / name) for name in ("summary.md", "reader.html")
        }
        bundle["next_actions"] = ["deliver reader.html and summary.md to the user"]
    else:
        bundle["next_actions"] = ["answer questions using chunks.json"]
    if not summary_mode and evidence_path.is_file():
        bundle["next_actions"].append("export evidence.json collections to CSV when requested")
    atomic_write_json(bundle_path, bundle)

    checks["bundle_updated"] = True
    return {
        "episode_dir": str(episode_dir),
        "status": "analyzed",
        "checks": checks,
        "errors": [],
        "valid": True,
        "artifacts": bundle["artifacts"]["analysis"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode_dir")
    args = parser.parse_args()
    result = finalize(Path(args.episode_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
