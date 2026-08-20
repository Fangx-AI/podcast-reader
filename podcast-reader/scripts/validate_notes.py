#!/usr/bin/env python3
"""Validate podcast-analysis Markdown for structure, evidence, and placeholders."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from evidence_validator import normalized_text, seconds, transcript_duration


TIMESTAMP = re.compile(r"\[(?:\d{1,3}:)?\d{2}:\d{2}(?:\s*[–—-]\s*(?:\d{1,3}:)?\d{2}:\d{2})?\]")
PLACEHOLDER = re.compile(r"\{(?:episode|title|source|show|date|duration|speaker|summary|topic)[^}]*\}|\b(?:TODO|TBD|FIXME)\b|（待补|待填写|待确认）", re.I)


def has_heading(text: str, words: tuple[str, ...]) -> bool:
    headings = re.findall(r"(?im)^##+\s+(.+)$", text)
    return any(any(word.casefold() in heading.casefold() for word in words) for heading in headings)


def validate(path: Path, strict: bool = False, transcript_path: Path | None = None) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    blockquotes = [
        match.group(0)
        for match in re.finditer(r"(?m)^>\s+.+$", text)
        if re.search(r"[“”\"]|—\s*\S", match.group(0))
    ]
    checks = {
        "h1_title": bool(re.search(r"(?m)^#\s+\S", text)),
        "source_provenance": bool(re.search(r"(?im)^[-|]\s*(?:source|来源|原始链接|节目链接)\s*[:|：]", text)),
        "summary": has_heading(text, ("总结", "summary", "核心结论", "executive")),
        "chapters_or_timeline": has_heading(text, ("章节", "时间线", "timeline", "chapter")),
        "evidence_timestamps": bool(TIMESTAMP.search(text)),
        "limitations": has_heading(text, ("限制", "不确定", "limitation", "uncertainty", "可信度")),
        "no_placeholders": not bool(PLACEHOLDER.search(text)),
        "quotes_are_timestamped": all(TIMESTAMP.search(quote) for quote in blockquotes),
    }
    transcript = None
    if transcript_path and transcript_path.is_file():
        try:
            transcript = json.loads(transcript_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            transcript = None
    timestamp_ranges_valid = True
    quotes_match_transcript = True
    if isinstance(transcript, dict):
        duration = transcript_duration(transcript)
        for match in TIMESTAMP.finditer(text):
            values = re.findall(r"(?:\d{1,3}:)?\d{2}:\d{2}", match.group(0))
            parsed = [seconds(value) for value in values]
            if any(value is None for value in parsed) or (len(parsed) == 2 and parsed[1] < parsed[0]) or any(value > duration + 2 for value in parsed if value is not None):
                timestamp_ranges_valid = False
                break
        for quote in blockquotes:
            quote_match = re.search(r"[“\"](?P<text>.+?)[”\"]", quote)
            stamp_match = TIMESTAMP.search(quote)
            if not quote_match or not stamp_match:
                continue
            stamps = re.findall(r"(?:\d{1,3}:)?\d{2}:\d{2}", stamp_match.group(0))
            start = seconds(stamps[0]) if stamps else None
            end = seconds(stamps[-1]) if len(stamps) > 1 else (start + 8 if start is not None else None)
            candidates = [
                str(item.get("text") or "") for item in transcript.get("segments", []) if isinstance(item, dict)
                and start is not None and end is not None
                and float(item.get("end_seconds") or item.get("start_seconds") or 0) >= start - 1
                and float(item.get("start_seconds") or 0) <= end + 1
            ]
            if normalized_text(quote_match.group("text")) not in normalized_text(" ".join(candidates)):
                quotes_match_transcript = False
                break
    checks["timestamp_ranges_valid"] = timestamp_ranges_valid
    checks["quotes_match_transcript"] = quotes_match_transcript
    required = ["h1_title", "source_provenance", "summary", "no_placeholders"]
    if strict:
        required.extend(["chapters_or_timeline", "evidence_timestamps", "limitations", "quotes_are_timestamped"])
        if transcript_path:
            required.extend(["timestamp_ranges_valid", "quotes_match_transcript"])
    failures = [name for name in required if not checks[name]]
    warnings = []
    if not checks["evidence_timestamps"]:
        warnings.append("No [HH:MM:SS] evidence timestamp was found.")
    if not checks["limitations"]:
        warnings.append("Add an uncertainty/limitations section.")
    if blockquotes and not checks["quotes_are_timestamped"]:
        warnings.append("Every quote block must include a timestamp on the same line.")
    if not checks["no_placeholders"]:
        warnings.append("Template placeholders or TODO markers remain.")
    if transcript_path and transcript is None:
        failures.append("transcript_unreadable")
    if not checks["timestamp_ranges_valid"]:
        warnings.append("One or more report timestamps are reversed or outside transcript duration.")
    if not checks["quotes_match_transcript"]:
        warnings.append("One or more quoted strings are not exact transcript substrings near their timestamps.")
    failures = list(dict.fromkeys(failures))
    return {"file": str(path.resolve()), "strict": strict, "checks": checks, "failures": failures, "warnings": warnings, "valid": not failures}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--transcript", help="Validate timestamp ranges and quoted text against transcript.json")
    args = parser.parse_args()
    result = validate(Path(args.markdown), args.strict, Path(args.transcript).expanduser().resolve() if args.transcript else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
