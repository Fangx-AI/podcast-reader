#!/usr/bin/env python3
"""Build a timestamp-preserving retrieval index from a normalized transcript."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path
from typing import Any


WORD = re.compile(r"[A-Za-z0-9_+#.-]{2,}|[\u3400-\u9fff]")
SENTENCE_BREAK = re.compile(r"(?<=[。！？!?；;\.])\s+|\n+")


def normalize_search_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def keywords(value: str, limit: int = 20) -> list[str]:
    counts = Counter(WORD.findall(value.casefold()))
    return [term for term, _ in counts.most_common(limit)]


def load_segments(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        raw = data.get("segments", []) if isinstance(data, dict) else data
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict) and str(item.get("text") or "").strip()]
    # Import beside this script only when non-normalized input is supplied.
    from normalize_transcript import load_segments as parse_segments, format_time
    result = []
    for index, item in enumerate(parse_segments(path), 1):
        start = item.get("start_seconds")
        end = item.get("end_seconds")
        result.append({
            "segment_id": index,
            "start": format_time(start),
            "end": format_time(end),
            "start_seconds": start,
            "end_seconds": end,
            "speaker": item.get("speaker"),
            "language": item.get("language"),
            "text": item.get("text"),
        })
    return result


def segment_seconds(item: dict[str, Any], field: str) -> float | None:
    value = item.get(field)
    return float(value) if isinstance(value, (int, float)) else None


def split_oversized_segments(segments: list[dict[str, Any]], max_chars: int) -> list[dict[str, Any]]:
    """Split a single huge untimed/plain-text segment before retrieval chunking."""
    expanded: list[dict[str, Any]] = []
    for segment in segments:
        text = str(segment.get("text") or "").strip()
        if len(text) <= max_chars:
            expanded.append(segment)
            continue
        units: list[str] = []
        for sentence in (part.strip() for part in SENTENCE_BREAK.split(text) if part.strip()):
            units.extend(sentence[index:index + max_chars] for index in range(0, len(sentence), max_chars))
        packed: list[str] = []
        current = ""
        for unit in units:
            candidate = f"{current} {unit}".strip()
            if current and len(candidate) > max_chars:
                packed.append(current)
                current = unit
            else:
                current = candidate
        if current:
            packed.append(current)
        start = segment_seconds(segment, "start_seconds")
        end = segment_seconds(segment, "end_seconds")
        total_chars = max(1, sum(len(part) for part in packed))
        consumed = 0
        for part_index, part in enumerate(packed, 1):
            clone = dict(segment)
            clone["source_segment_id"] = segment.get("segment_id")
            clone["segment_id"] = f"{segment.get('segment_id', len(expanded) + 1)}.{part_index}"
            if start is not None and end is not None and end > start:
                clone["start_seconds"] = start + (end - start) * consumed / total_chars
                consumed += len(part)
                clone["end_seconds"] = start + (end - start) * consumed / total_chars
                from normalize_transcript import format_time
                clone["start"] = format_time(clone["start_seconds"])
                clone["end"] = format_time(clone["end_seconds"])
            clone["text"] = part
            expanded.append(clone)
    return expanded


def should_flush(group: list[dict[str, Any]], candidate: dict[str, Any], max_chars: int, max_seconds: int) -> bool:
    if not group:
        return False
    char_total = sum(len(str(item.get("text") or "")) for item in group) + len(str(candidate.get("text") or ""))
    if char_total > max_chars:
        return True
    start = segment_seconds(group[0], "start_seconds")
    end = segment_seconds(candidate, "end_seconds") or segment_seconds(candidate, "start_seconds")
    return start is not None and end is not None and end - start > max_seconds


def make_chunk(chunk_id: int, group: list[dict[str, Any]]) -> dict[str, Any]:
    text = " ".join(str(item.get("text") or "").strip() for item in group).strip()
    speakers = list(dict.fromkeys(str(item["speaker"]) for item in group if item.get("speaker")))
    start_seconds = segment_seconds(group[0], "start_seconds")
    end_seconds = segment_seconds(group[-1], "end_seconds") or segment_seconds(group[-1], "start_seconds")
    return {
        "chunk_id": chunk_id,
        "segment_ids": [item.get("segment_id", index + 1) for index, item in enumerate(group)],
        "start": group[0].get("start"),
        "end": group[-1].get("end") or group[-1].get("start"),
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "speakers": speakers,
        "char_count": len(text),
        "keyword_hints": keywords(text),
        "text": text,
        "search_text": normalize_search_text(text),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript")
    parser.add_argument("-o", "--output")
    parser.add_argument("--max-chars", type=int, default=3600)
    parser.add_argument("--max-seconds", type=int, default=300)
    parser.add_argument("--overlap-segments", type=int, default=2)
    args = parser.parse_args()
    if args.max_chars < 200:
        raise ValueError("--max-chars must be at least 200")
    if args.overlap_segments < 0:
        raise ValueError("--overlap-segments cannot be negative")

    source = Path(args.transcript).expanduser().resolve()
    source_segments = load_segments(source)
    segments = split_oversized_segments(source_segments, args.max_chars)
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for segment in segments:
        if should_flush(current, segment, args.max_chars, args.max_seconds):
            groups.append(current)
            current = current[-args.overlap_segments:] if args.overlap_segments else []
            while current and sum(len(str(item.get("text") or "")) for item in current) + len(str(segment.get("text") or "")) > args.max_chars:
                current.pop(0)
        current.append(segment)
    if current:
        groups.append(current)
    chunks = [make_chunk(index, group) for index, group in enumerate(groups)]
    document = {
        "schema_version": "1.0",
        "source": str(source),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "segment_count": len(source_segments),
        "indexed_segment_count": len(segments),
        "chunk_count": len(chunks),
        "settings": {"max_chars": args.max_chars, "max_seconds": args.max_seconds, "overlap_segments": args.overlap_segments},
        "chunks": chunks,
    }
    output = Path(args.output).expanduser().resolve() if args.output else source.with_name("chunks.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ready", "output": str(output), "segment_count": len(source_segments), "indexed_segment_count": len(segments), "chunk_count": len(chunks)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
