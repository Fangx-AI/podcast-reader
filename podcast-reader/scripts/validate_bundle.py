#!/usr/bin/env python3
"""Validate an episode bundle's manifest, transcript, index, and artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


READY_STATUSES = {"ready", "ready_for_analysis", "analyzed"}


def read_json(path: Path, errors: list[str]):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        errors.append(f"invalid JSON {path.name}: {exc}")
        return None


def validate(episode_dir: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, bool] = {}
    manifest_path = episode_dir / "bundle.json"
    checks["bundle_json_exists"] = manifest_path.is_file()
    if not checks["bundle_json_exists"]:
        errors.append("bundle.json is missing")
        return {"episode_dir": str(episode_dir), "checks": checks, "errors": errors, "warnings": warnings, "valid": False}
    bundle = read_json(manifest_path, errors)
    if not isinstance(bundle, dict):
        return {"episode_dir": str(episode_dir), "checks": checks, "errors": errors, "warnings": warnings, "valid": False}

    checks["schema_version"] = bundle.get("schema_version") == "1.0"
    checks["source_identity"] = bool(bundle.get("bundle_id") and bundle.get("source_input"))
    checks["status"] = bool(bundle.get("status"))
    checks["next_actions"] = isinstance(bundle.get("next_actions"), list) and bool(bundle.get("next_actions"))
    for name in ("schema_version", "source_identity", "status", "next_actions"):
        if not checks[name]:
            errors.append(f"bundle check failed: {name}")

    transcript_path = episode_dir / "transcript.json"
    chunks_path = episode_dir / "chunks.json"
    source_path = episode_dir / "source.json"
    checks["source_exists"] = source_path.is_file()
    if not source_path.is_file():
        errors.append("source.json is missing")
    elif not isinstance(read_json(source_path, errors), dict):
        errors.append("source.json must contain a JSON object")
    checks["transcript_exists"] = transcript_path.is_file()
    checks["index_exists"] = chunks_path.is_file()
    if bundle.get("status") in READY_STATUSES or bundle.get("transcript_status") == "normalized":
        if not transcript_path.is_file():
            errors.append("ready bundle is missing transcript.json")
        if not chunks_path.is_file():
            errors.append("ready bundle is missing chunks.json")

    transcript = read_json(transcript_path, errors) if transcript_path.is_file() else None
    chunks = read_json(chunks_path, errors) if chunks_path.is_file() else None
    if isinstance(transcript, dict):
        segments = transcript.get("segments")
        checks["transcript_schema"] = transcript.get("schema_version") == "1.0" and isinstance(segments, list) and bool(segments)
        checks["transcript_text"] = bool(segments) and all(isinstance(item, dict) and str(item.get("text") or "").strip() for item in segments)
        if not checks["transcript_schema"] or not checks["transcript_text"]:
            errors.append("transcript.json has invalid or empty segments")
    if isinstance(chunks, dict):
        indexed = chunks.get("chunks")
        checks["chunks_schema"] = chunks.get("schema_version") == "1.0" and isinstance(indexed, list) and bool(indexed)
        checks["chunks_searchable"] = bool(indexed) and all(str(item.get("text") or "").strip() and "chunk_id" in item for item in indexed)
        if not checks["chunks_schema"] or not checks["chunks_searchable"]:
            errors.append("chunks.json has invalid or empty chunks")
        if isinstance(transcript, dict) and chunks.get("segment_count") != transcript.get("segment_count"):
            warnings.append("chunk index segment_count differs from transcript")

    inventory = bundle.get("artifacts")
    checks["artifact_inventory"] = isinstance(inventory, dict)
    if isinstance(inventory, dict):
        for category, paths in inventory.items():
            if not isinstance(paths, list):
                errors.append(f"artifact category is not a list: {category}")
                continue
            for relative in paths:
                candidate = (episode_dir / relative).resolve()
                try:
                    candidate.relative_to(episode_dir.resolve())
                except ValueError:
                    errors.append(f"artifact escapes episode directory: {relative}")
                    continue
                if not candidate.is_file():
                    warnings.append(f"inventory artifact is missing: {relative}")
    if list(episode_dir.rglob("*.part")):
        warnings.append("incomplete .part files remain")
    result = {"episode_dir": str(episode_dir.resolve()), "status": bundle.get("status"), "checks": checks, "errors": errors, "warnings": warnings, "valid": not errors}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode_dir")
    args = parser.parse_args()
    result = validate(Path(args.episode_dir).expanduser().resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
