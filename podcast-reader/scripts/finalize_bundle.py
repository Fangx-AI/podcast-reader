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
        "analysis_exists": analysis_path.is_file(),
    }
    if not all(checks.values()):
        missing = [name for name, passed in checks.items() if not passed]
        return {"episode_dir": str(episode_dir), "checks": checks, "errors": missing, "valid": False}

    bundle = load_json(bundle_path)
    transcript = load_json(transcript_path)
    errors: list[str] = []

    analysis_result = validate_notes(analysis_path, strict=True)
    checks["analysis_strict"] = bool(analysis_result["valid"])
    if not checks["analysis_strict"]:
        errors.extend(f"analysis:{failure}" for failure in analysis_result["failures"])

    if summary_path.is_file():
        summary_result = validate_notes(summary_path, strict=True)
        checks["summary_strict"] = bool(summary_result["valid"])
        if not checks["summary_strict"]:
            errors.extend(f"summary:{failure}" for failure in summary_result["failures"])

    if evidence_path.is_file():
        try:
            evidence = load_json(evidence_path)
            segment_ids = {
                int(segment["segment_id"])
                for segment in transcript.get("segments", [])
                if isinstance(segment, dict) and isinstance(segment.get("segment_id"), int)
            }
            missing_ids = sorted(evidence_segment_ids(evidence) - segment_ids)
            checks["evidence_json"] = isinstance(evidence, dict) and evidence.get("schema_version") == "1.0"
            checks["evidence_references"] = not missing_ids
            if not checks["evidence_json"]:
                errors.append("evidence:invalid_schema")
            if missing_ids:
                errors.append(f"evidence:missing_segment_ids:{','.join(map(str, missing_ids))}")
        except (OSError, ValueError, TypeError) as exc:
            checks["evidence_json"] = False
            checks["evidence_references"] = False
            errors.append(f"evidence:{exc}")

    if errors:
        return {"episode_dir": str(episode_dir), "checks": checks, "errors": errors, "valid": False}

    bundle["status"] = "analyzed"
    bundle["updated_at"] = datetime.now(timezone.utc).isoformat()
    bundle["artifacts"] = artifact_inventory(episode_dir)
    bundle["next_actions"] = ["answer questions using chunks.json"]
    if evidence_path.is_file():
        bundle["next_actions"].append("export evidence.json collections to CSV when requested")
    else:
        bundle["next_actions"].append("create evidence.json when structured evidence or CSV export is requested")
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

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
