#!/usr/bin/env python3
"""Validate podcast-analysis Markdown for structure, evidence, and placeholders."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


TIMESTAMP = re.compile(r"\[(?:\d{1,3}:)?\d{2}:\d{2}(?:\s*[–—-]\s*(?:\d{1,3}:)?\d{2}:\d{2})?\]")
PLACEHOLDER = re.compile(r"\{(?:episode|title|source|show|date|duration|speaker|summary|topic)[^}]*\}|\b(?:TODO|TBD|FIXME)\b|（待补|待填写|待确认）", re.I)


def has_heading(text: str, words: tuple[str, ...]) -> bool:
    headings = re.findall(r"(?im)^##+\s+(.+)$", text)
    return any(any(word.casefold() in heading.casefold() for word in words) for heading in headings)


def validate(path: Path, strict: bool = False) -> dict:
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
    required = ["h1_title", "source_provenance", "summary", "no_placeholders"]
    if strict:
        required.extend(["chapters_or_timeline", "evidence_timestamps", "limitations", "quotes_are_timestamped"])
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
    return {"file": str(path.resolve()), "strict": strict, "checks": checks, "failures": failures, "warnings": warnings, "valid": not failures}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    result = validate(Path(args.markdown), args.strict)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
