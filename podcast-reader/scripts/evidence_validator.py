#!/usr/bin/env python3
"""Strict, dependency-free validation for Podcast Reader evidence artifacts."""

from __future__ import annotations

import re
from typing import Any
import argparse


CLAIM_KINDS = {"fact", "opinion", "anecdote", "prediction", "recommendation", "synthesis"}
SUPPORT_KINDS = {"stated", "illustrated", "argued", "asserted", "contradicted"}
CONFIDENCE_LEVELS = {"high", "medium", "low"}
VERIFICATION_STATES = {"not_checked", "supported", "mixed", "contradicted", "outdated", "not_verifiable"}
ENTITY_TYPES = {"person", "organization", "product", "book", "paper", "concept", "tool"}
COLLECTIONS = ("chapters", "claims", "quotes", "actions", "entities", "glossary", "visual_evidence", "limitations")


def seconds(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str) or not value.strip():
        return None
    parts = value.strip().replace(",", ".").split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
    except ValueError:
        return None
    return None


def normalized_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def segment_map(transcript: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {
        item["segment_id"]: item
        for item in transcript.get("segments", [])
        if isinstance(item, dict) and isinstance(item.get("segment_id"), int)
    }


def transcript_duration(transcript: dict[str, Any]) -> float:
    values = [
        float(item.get("end_seconds") or item.get("start_seconds") or 0)
        for item in transcript.get("segments", []) if isinstance(item, dict)
    ]
    return max(values, default=0.0)


def validate_timestamp_range(start: Any, end: Any, duration: float, label: str, errors: list[str]) -> tuple[float | None, float | None]:
    start_value = seconds(start)
    end_value = seconds(end)
    if start_value is None or end_value is None:
        errors.append(f"{label}: invalid timestamp range")
        return start_value, end_value
    if start_value < 0 or end_value < start_value:
        errors.append(f"{label}: timestamp range is reversed or negative")
    if duration and end_value > duration + 2:
        errors.append(f"{label}: timestamp exceeds transcript duration")
    return start_value, end_value


def validate_reference(reference: Any, segments: dict[int, dict[str, Any]], duration: float, label: str, errors: list[str]) -> set[int]:
    if not isinstance(reference, dict):
        errors.append(f"{label}: evidence reference must be an object")
        return set()
    ids = reference.get("segment_ids")
    if not isinstance(ids, list) or not ids or any(not isinstance(item, int) for item in ids):
        errors.append(f"{label}: segment_ids must be a non-empty integer list")
        return set()
    missing = sorted(set(ids) - set(segments))
    if missing:
        errors.append(f"{label}: unknown segment_ids {missing}")
    start = reference.get("start")
    end = reference.get("end")
    if start is not None or end is not None:
        start_value, end_value = validate_timestamp_range(start, end, duration, label, errors)
        referenced = [segments[item] for item in ids if item in segments]
        if referenced and start_value is not None and end_value is not None:
            min_start = min(float(item.get("start_seconds") or 0) for item in referenced)
            max_end = max(float(item.get("end_seconds") or item.get("start_seconds") or 0) for item in referenced)
            if start_value > max_end + 2 or end_value < min_start - 2:
                errors.append(f"{label}: timestamps do not overlap referenced segments")
    return set(item for item in ids if item in segments)


def _validate_evidence_list(item: dict[str, Any], segments: dict[int, dict[str, Any]], duration: float, label: str, errors: list[str], required: bool = True) -> set[int]:
    evidence = item.get("evidence")
    if not isinstance(evidence, list) or (required and not evidence):
        errors.append(f"{label}: evidence must be a non-empty list")
        return set()
    found: set[int] = set()
    for index, reference in enumerate(evidence):
        found.update(validate_reference(reference, segments, duration, f"{label}.evidence[{index}]", errors))
    return found


def validate_evidence(document: Any, transcript: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(document, dict):
        return {"valid": False, "errors": ["evidence root must be an object"], "warnings": []}
    if document.get("schema_version") not in {"1.0", "2.0"}:
        errors.append("schema_version must be 1.0 or 2.0")
    for collection in COLLECTIONS:
        value = document.get(collection, [])
        if not isinstance(value, list):
            errors.append(f"{collection} must be a list")
    segments = segment_map(transcript)
    duration = transcript_duration(transcript)
    if not segments:
        errors.append("transcript contains no addressable segments")

    previous_end = -1.0
    for index, item in enumerate(document.get("chapters", []) if isinstance(document.get("chapters"), list) else []):
        label = f"chapters[{index}]"
        if not isinstance(item, dict) or not str(item.get("title") or "").strip():
            errors.append(f"{label}: title is required")
            continue
        start, end = validate_timestamp_range(item.get("start"), item.get("end"), duration, label, errors)
        if start is not None and start < previous_end - 1:
            errors.append(f"{label}: chapters are out of order or overlap")
        if end is not None:
            previous_end = end

    for index, item in enumerate(document.get("claims", []) if isinstance(document.get("claims"), list) else []):
        label = f"claims[{index}]"
        if not isinstance(item, dict) or not str(item.get("claim") or "").strip():
            errors.append(f"{label}: claim text is required")
            continue
        for field, allowed in (("kind", CLAIM_KINDS), ("support", SUPPORT_KINDS), ("confidence", CONFIDENCE_LEVELS), ("verification", VERIFICATION_STATES)):
            if item.get(field) not in allowed:
                errors.append(f"{label}: invalid {field}")
        _validate_evidence_list(item, segments, duration, label, errors)

    for index, item in enumerate(document.get("quotes", []) if isinstance(document.get("quotes"), list) else []):
        label = f"quotes[{index}]"
        if not isinstance(item, dict) or not normalized_text(item.get("text")):
            errors.append(f"{label}: quote text is required")
            continue
        start, end = validate_timestamp_range(item.get("start"), item.get("end"), duration, label, errors)
        ids = item.get("segment_ids")
        if isinstance(ids, list) and ids:
            matched_ids = validate_reference({"segment_ids": ids, "start": item.get("start"), "end": item.get("end")}, segments, duration, label, errors)
        else:
            matched_ids = {
                segment_id for segment_id, segment in segments.items()
                if start is not None and end is not None
                and float(segment.get("end_seconds") or segment.get("start_seconds") or 0) >= start - 1
                and float(segment.get("start_seconds") or 0) <= end + 1
            }
        source_text = normalized_text(" ".join(str(segments[item].get("text") or "") for item in sorted(matched_ids)))
        if not source_text or normalized_text(item.get("text")) not in source_text:
            errors.append(f"{label}: quote text is not an exact substring of referenced transcript evidence")

    for collection, text_field, evidence_required in (("actions", "action", True), ("entities", "name", True), ("glossary", "source_term", False)):
        for index, item in enumerate(document.get(collection, []) if isinstance(document.get(collection), list) else []):
            label = f"{collection}[{index}]"
            if not isinstance(item, dict) or not str(item.get(text_field) or "").strip():
                errors.append(f"{label}: {text_field} is required")
                continue
            if collection == "entities" and item.get("type") not in ENTITY_TYPES:
                errors.append(f"{label}: invalid type")
            _validate_evidence_list(item, segments, duration, label, errors, required=evidence_required)

    if not document.get("claims"):
        warnings.append("evidence contains no claims")
    coverage_ids: set[int] = set()
    for collection in ("claims", "actions", "entities"):
        for item in document.get(collection, []) if isinstance(document.get(collection), list) else []:
            if isinstance(item, dict):
                for reference in item.get("evidence", []) if isinstance(item.get("evidence"), list) else []:
                    if isinstance(reference, dict):
                        coverage_ids.update(value for value in reference.get("segment_ids", []) if isinstance(value, int))
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "transcript_segments": len(segments),
            "cited_segments": len(coverage_ids & set(segments)),
            "citation_coverage": round(len(coverage_ids & set(segments)) / len(segments), 4) if segments else 0.0,
            "claims": len(document.get("claims", [])) if isinstance(document.get("claims"), list) else 0,
            "quotes": len(document.get("quotes", [])) if isinstance(document.get("quotes"), list) else 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print("Podcast Reader evidence validation library; use validate_evidence.py for files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
