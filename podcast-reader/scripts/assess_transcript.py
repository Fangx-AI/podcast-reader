#!/usr/bin/env python3
"""Assess transcript timing, confidence, repetition, and boundary risk without external services."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any

from runtime_utils import atomic_write_json


def repeated_pattern_span(text: str) -> int:
    """Return the longest suspicious repeated span, including CJK text without spaces."""
    collapsed = re.sub(r"\s+", "", text.casefold())
    longest = max((len(match.group(0)) for match in re.finditer(r"(.)\1{11,}", collapsed)), default=0)
    for width in range(2, min(13, len(collapsed) // 8 + 1)):
        pattern = re.compile(rf"(.{{{width}}})\1{{7,}}")
        longest = max(longest, max((len(match.group(0)) for match in pattern.finditer(collapsed)), default=0))
    return longest


def assess(document: dict[str, Any]) -> dict[str, Any]:
    segments = [item for item in document.get("segments", []) if isinstance(item, dict)]
    errors: list[str] = []
    warnings: list[str] = []
    if not segments:
        return {"status": "fail", "score": 0, "errors": ["no transcript segments"], "warnings": [], "metrics": {}}
    timed = [item for item in segments if isinstance(item.get("start_seconds"), (int, float)) and isinstance(item.get("end_seconds"), (int, float))]
    reversed_ranges = sum(float(item["end_seconds"]) < float(item["start_seconds"]) for item in timed)
    if reversed_ranges:
        errors.append(f"{reversed_ranges} reversed timestamp ranges")
    texts = [re.sub(r"\s+", " ", str(item.get("text") or "")).strip() for item in segments]
    empty = sum(not text for text in texts)
    if empty:
        errors.append(f"{empty} empty segments")
    normalized = [text.casefold() for text in texts if text]
    repetitions = sum(count - 1 for count in Counter(normalized).values() if count > 1)
    if repetitions / max(1, len(normalized)) > 0.15:
        warnings.append("high exact-segment repetition; inspect chunk joins or caption rolling text")
    suspicious = [text for text in texts if len(text.split()) >= 8 and len(set(text.casefold().split())) <= 2]
    if suspicious:
        warnings.append("possible repeated-token ASR hallucination")
    pathological = []
    for index, text in enumerate(texts):
        repeated_span = repeated_pattern_span(text)
        if repeated_span >= 32:
            pathological.append({"segment_id": segments[index].get("segment_id", index + 1), "repeated_span": repeated_span})
    if pathological:
        warnings.append(
            "possible within-segment ASR repetition in segment(s): "
            + ", ".join(str(item["segment_id"]) for item in pathological[:12])
        )
    confidence_values = [float(item["confidence"]) for item in segments if isinstance(item.get("confidence"), (int, float))]
    low_confidence = sum(value < 0.5 for value in confidence_values)
    if confidence_values and low_confidence / len(confidence_values) > 0.2:
        warnings.append("more than 20% of scored segments have low confidence")
    durations = [max(0.0, float(item["end_seconds"]) - float(item["start_seconds"])) for item in timed]
    words = sum(len(text.split()) for text in texts)
    total_seconds = max((float(item["end_seconds"]) for item in timed), default=0.0)
    characters = sum(len(text) for text in texts)
    score = 100 - 30 * bool(errors) - min(25, len(warnings) * 10)
    if len(timed) / len(segments) < 0.95:
        warnings.append("fewer than 95% of segments are timestamped")
        score -= 15
    score = max(0, min(100, score))
    return {
        "schema_version": "2.0",
        "status": "fail" if errors else "warn" if warnings else "pass",
        "score": score,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "segments": len(segments), "timed_segments": len(timed), "timed_coverage": round(len(timed) / len(segments), 4),
            "duration_seconds": round(total_seconds, 3), "speech_seconds": round(sum(durations), 3),
            "characters": characters, "words": words, "exact_repetitions": repetitions,
            "pathological_segments": len(pathological),
            "pathological_segment_ids": [item["segment_id"] for item in pathological],
            "max_repeated_span": max((item["repeated_span"] for item in pathological), default=0),
            "confidence_samples": len(confidence_values), "average_confidence": round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else None,
            "low_confidence_segments": low_confidence,
        },
        "spot_check": ["speaker introductions", "proper nouns", "numbers and dates", "negation", "selected direct quotes"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript")
    parser.add_argument("--output")
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    try:
        source = Path(args.transcript).expanduser().resolve()
        document = json.loads(source.read_text(encoding="utf-8-sig"))
        result = assess(document)
        output = Path(args.output).expanduser().resolve() if args.output else source.with_name("transcript-quality.json")
        atomic_write_json(output, result)
        result["output"] = str(output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result["status"] == "fail" or (args.require_pass and result["status"] != "pass") else 0
    except Exception as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
