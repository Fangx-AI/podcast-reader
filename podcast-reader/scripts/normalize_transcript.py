#!/usr/bin/env python3
"""Normalize common transcript formats and export JSON, Markdown, SRT, and VTT."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


TIME_RANGE = re.compile(
    r"(?P<start>(?:\d{1,3}:)?\d{1,2}:\d{2}(?:[,.]\d{1,3})?)\s*-->\s*"
    r"(?P<end>(?:\d{1,3}:)?\d{1,2}:\d{2}(?:[,.]\d{1,3})?)"
)
BRACKET_TIME = re.compile(r"^\s*\[(?P<time>(?:\d{1,3}:)?\d{1,2}:\d{2}(?:[,.]\d{1,3})?)\]\s*(?P<text>.*)$")
SPEAKER_PREFIX = re.compile(r"^(?P<speaker>[^:：]{1,60})[:：]\s+(?P<text>.+)$")
VOICE_TAG = re.compile(r"<v(?:\.[^ >]+)?\s+([^>]+)>(.*?)</v>", re.I | re.S)


def time_to_seconds(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", ".")
    if text.endswith("ms"):
        try:
            return float(text[:-2]) / 1000
        except ValueError:
            return None
    if text.endswith("s"):
        try:
            return float(text[:-1])
        except ValueError:
            return None
    if text.isdigit():
        return float(text)
    parts = text.split(":")
    try:
        numbers = [float(part) for part in parts]
    except ValueError:
        return None
    if len(numbers) == 3:
        return numbers[0] * 3600 + numbers[1] * 60 + numbers[2]
    if len(numbers) == 2:
        return numbers[0] * 60 + numbers[1]
    return numbers[0] if len(numbers) == 1 else None


def format_time(seconds: float | None, milliseconds: bool = False, comma: bool = False) -> str | None:
    if seconds is None:
        return None
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    whole = int(seconds % 60)
    if milliseconds:
        millis = int(round((seconds - int(seconds)) * 1000))
        if millis == 1000:
            seconds += 1
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            whole = int(seconds % 60)
            millis = 0
        separator = "," if comma else "."
        return f"{hours:02d}:{minutes:02d}:{whole:02d}{separator}{millis:03d}"
    return f"{hours:02d}:{minutes:02d}:{whole:02d}"


def clean_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"</?c(?:\.[^ >]+)?>", "", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    value = value.replace("\u200b", " ").replace("\ufeff", "")
    return re.sub(r"\s+", " ", value).strip()


def parse_speaker(value: str) -> tuple[str | None, str]:
    voice = VOICE_TAG.search(value)
    if voice:
        return clean_text(voice.group(1)), clean_text(voice.group(2))
    cleaned = clean_text(value)
    match = SPEAKER_PREFIX.match(cleaned)
    if match and len(match.group("speaker").split()) <= 8:
        return match.group("speaker").strip(), match.group("text").strip()
    return None, cleaned


def parse_caption_text(text: str) -> list[dict[str, Any]]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    segments: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        match = TIME_RANGE.search(line)
        if not match:
            index += 1
            continue
        start = time_to_seconds(match.group("start"))
        end = time_to_seconds(match.group("end"))
        index += 1
        parts: list[str] = []
        while index < len(lines) and lines[index].strip():
            parts.append(lines[index].strip())
            index += 1
        raw = " ".join(parts)
        speaker, cleaned = parse_speaker(raw)
        if cleaned:
            segments.append({"start_seconds": start, "end_seconds": end, "speaker": speaker, "text": cleaned})
        index += 1
    return segments


def parse_plain_text(text: str) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    untimed: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = BRACKET_TIME.match(stripped)
        if match:
            speaker, cleaned = parse_speaker(match.group("text"))
            segments.append({"start_seconds": time_to_seconds(match.group("time")), "end_seconds": None, "speaker": speaker, "text": cleaned})
        elif not stripped.startswith("#"):
            untimed.append(stripped)
    if segments:
        for pos, segment in enumerate(segments[:-1]):
            if segment["end_seconds"] is None:
                segment["end_seconds"] = segments[pos + 1]["start_seconds"]
        return segments
    cleaned = clean_text(" ".join(untimed))
    return [{"start_seconds": None, "end_seconds": None, "speaker": None, "text": cleaned}] if cleaned else []


def parse_ass_text(text: str) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.lstrip().casefold().startswith("dialogue:"):
            continue
        fields = line.split(":", 1)[1].split(",", 9)
        if len(fields) != 10:
            continue
        start, end, speaker, content = fields[1], fields[2], fields[4].strip() or None, fields[9]
        content = re.sub(r"\{[^}]*\}", "", content).replace(r"\N", " ").replace(r"\n", " ")
        cleaned = clean_text(content)
        if cleaned:
            segments.append({"start_seconds": time_to_seconds(start), "end_seconds": time_to_seconds(end), "speaker": speaker, "text": cleaned})
    return segments


def parse_ttml_text(text: str) -> list[dict[str, Any]]:
    root = ET.fromstring(text)
    segments: list[dict[str, Any]] = []
    for node in root.iter():
        if node.tag.rsplit("}", 1)[-1].casefold() != "p":
            continue
        content = clean_text(" ".join(node.itertext()))
        if not content:
            continue
        start = time_to_seconds(node.attrib.get("begin"))
        end = time_to_seconds(node.attrib.get("end"))
        if end is None and start is not None:
            duration = time_to_seconds(node.attrib.get("dur"))
            end = start + duration if duration is not None else None
        speaker = node.attrib.get("speaker") or node.attrib.get("voice")
        segments.append({"start_seconds": start, "end_seconds": end, "speaker": speaker, "text": content})
    return segments


def _pick_segments(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("segments", "utterances", "cues", "transcript"):
            nested = value.get(key)
            if isinstance(nested, list):
                return nested
            if isinstance(nested, dict):
                selected = _pick_segments(nested)
                if selected:
                    return selected
    return []


def parse_json_data(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("events"), list):
        json3_segments: list[dict[str, Any]] = []
        for event in data["events"]:
            if not isinstance(event, dict):
                continue
            text = clean_text("".join(str(part.get("utf8") or "") for part in event.get("segs", []) if isinstance(part, dict)))
            if not text:
                continue
            start = float(event.get("tStartMs") or 0) / 1000
            duration = float(event.get("dDurationMs") or 0) / 1000
            json3_segments.append({"start_seconds": start, "end_seconds": start + duration if duration else None, "speaker": None, "text": text})
        return json3_segments
    items = _pick_segments(data)
    segments: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = item.get("text") or item.get("transcript") or item.get("content") or ""
        text = clean_text(str(text))
        if not text:
            continue
        start = item.get("start_seconds", item.get("start", item.get("begin")))
        end = item.get("end_seconds", item.get("end", item.get("finish")))
        # Some APIs use milliseconds. Only convert explicit *_ms fields automatically.
        if item.get("start_ms") is not None:
            start = float(item["start_ms"]) / 1000
        if item.get("end_ms") is not None:
            end = float(item["end_ms"]) / 1000
        segments.append({
            "start_seconds": time_to_seconds(start),
            "end_seconds": time_to_seconds(end),
            "speaker": item.get("speaker") or item.get("speaker_name") or item.get("speaker_label"),
            "language": item.get("language"),
            "confidence": item.get("confidence"),
            "text": text,
        })
    return segments


def deduplicate(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for segment in segments:
        text = clean_text(str(segment.get("text") or ""))
        if not text:
            continue
        segment = dict(segment)
        segment["text"] = text
        if result and text == result[-1]["text"] and segment.get("speaker") == result[-1].get("speaker"):
            if segment.get("end_seconds") is not None:
                result[-1]["end_seconds"] = segment["end_seconds"]
            continue
        if result and segment.get("speaker") == result[-1].get("speaker") and text.startswith(result[-1]["text"]):
            previous_end = result[-1].get("end_seconds")
            current_start = segment.get("start_seconds")
            if previous_end is None or current_start is None or current_start <= previous_end + 1:
                result[-1]["text"] = text
                result[-1]["end_seconds"] = segment.get("end_seconds") or previous_end
                continue
        result.append(segment)
    return result


def load_segments(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".json", ".json3"}:
        segments = parse_json_data(json.loads(path.read_text(encoding="utf-8-sig")))
    else:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if suffix == ".ass":
            segments = parse_ass_text(text)
        elif suffix in {".ttml", ".xml"}:
            segments = parse_ttml_text(text)
        elif suffix in {".srt", ".vtt"} or TIME_RANGE.search(text):
            segments = parse_caption_text(text)
        else:
            segments = parse_plain_text(text)
    return deduplicate(segments)


def normalized_document(source: Path, segments: list[dict[str, Any]], language: str | None, method: str) -> dict[str, Any]:
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(segments, 1):
        start = time_to_seconds(item.get("start_seconds"))
        end = time_to_seconds(item.get("end_seconds"))
        normalized.append({
            "segment_id": index,
            "start": format_time(start),
            "end": format_time(end),
            "start_seconds": start,
            "end_seconds": end,
            "speaker": item.get("speaker"),
            "language": item.get("language") or language,
            "confidence": item.get("confidence"),
            "text": item["text"],
        })
    timed = [item for item in normalized if item["start_seconds"] is not None]
    speakers = sorted({str(item["speaker"]) for item in normalized if item.get("speaker")})
    return {
        "schema_version": "1.0",
        "source_file": str(source.resolve()),
        "normalized_at": datetime.now(timezone.utc).isoformat(),
        "method": method,
        "language": language,
        "segment_count": len(normalized),
        "timed_segment_count": len(timed),
        "speaker_count": len(speakers),
        "speakers": speakers,
        "duration_seconds": max((item.get("end_seconds") or item.get("start_seconds") or 0 for item in normalized), default=None),
        "segments": normalized,
    }


def write_markdown(document: dict[str, Any], path: Path) -> None:
    lines = ["# Timestamped transcript", "", f"- Source file: `{document['source_file']}`", f"- Method: {document['method']}", f"- Language: {document.get('language') or 'unknown'}", f"- Segments: {document['segment_count']}", ""]
    for item in document["segments"]:
        stamp = item.get("start")
        speaker = item.get("speaker")
        prefix = f"[{stamp}] " if stamp else ""
        if speaker:
            prefix += f"**{speaker}:** "
        lines.append(prefix + item["text"])
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_srt(document: dict[str, Any], path: Path) -> bool:
    timed = [item for item in document["segments"] if item.get("start_seconds") is not None]
    if not timed:
        return False
    lines: list[str] = []
    for index, item in enumerate(timed, 1):
        start = item["start_seconds"]
        end = item.get("end_seconds")
        if end is None or end <= start:
            end = timed[index]["start_seconds"] if index < len(timed) else start + 4
        label = f"{item['speaker']}: " if item.get("speaker") else ""
        lines.extend([str(index), f"{format_time(start, True, True)} --> {format_time(end, True, True)}", label + item["text"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return True


def write_vtt(document: dict[str, Any], path: Path) -> bool:
    timed = [item for item in document["segments"] if item.get("start_seconds") is not None]
    if not timed:
        return False
    lines = ["WEBVTT", ""]
    for index, item in enumerate(timed):
        start = item["start_seconds"]
        end = item.get("end_seconds")
        if end is None or end <= start:
            end = timed[index + 1]["start_seconds"] if index + 1 < len(timed) else start + 4
        text = f"<v {item['speaker']}>{item['text']}</v>" if item.get("speaker") else item["text"]
        lines.extend([f"{format_time(start, True)} --> {format_time(end, True)}", text, ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript")
    parser.add_argument("--output-dir")
    parser.add_argument("--language")
    parser.add_argument("--method", default="normalized", help="official, human_captions, automatic_captions, generated, or normalized")
    parser.add_argument("--no-subtitles", action="store_true", help="Do not generate SRT/VTT exports")
    args = parser.parse_args()

    source = Path(args.transcript).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else source.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    document = normalized_document(source, load_segments(source), args.language, args.method)
    if not document["segments"]:
        raise ValueError("no transcript segments could be parsed")
    json_path = output_dir / "transcript.json"
    md_path = output_dir / "transcript.md"
    json_path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(document, md_path)
    exports = {"json": str(json_path), "markdown": str(md_path)}
    if not args.no_subtitles:
        srt_path, vtt_path = output_dir / "transcript.srt", output_dir / "transcript.vtt"
        if write_srt(document, srt_path):
            exports["srt"] = str(srt_path)
        if write_vtt(document, vtt_path):
            exports["vtt"] = str(vtt_path)
    print(json.dumps({"status": "ready", "segment_count": document["segment_count"], "timed_segment_count": document["timed_segment_count"], "exports": exports}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
