#!/usr/bin/env python3
"""Create or apply a timestamp-preserving, provider-neutral transcript translation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any

from normalize_transcript import write_markdown, write_srt, write_vtt
from runtime_utils import atomic_write_json


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def language_slug(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    if not result:
        raise ValueError("target language must contain a portable language code")
    return result


def create_request(transcript: dict[str, Any], target_language: str, output: Path) -> dict[str, Any]:
    request = {
        "schema_version": "2.0", "status": "awaiting_agent_translation", "target_language": target_language,
        "instructions": [
            "Translate text only; preserve segment_id exactly.",
            "Do not merge, split, omit, or reorder segments.",
            "Keep names, products, acronyms, numbers, negation, and uncertainty faithful.",
            "Return JSON with target_language and segments[{segment_id,text}].",
        ],
        "segments": [{"segment_id": item.get("segment_id"), "speaker": item.get("speaker"), "text": item.get("text")} for item in transcript.get("segments", []) if isinstance(item, dict)],
    }
    atomic_write_json(output, request)
    return {"status": "awaiting_agent_translation", "request": str(output), "segments": len(request["segments"]), "target_language": target_language}


def apply_translation(transcript: dict[str, Any], translation: dict[str, Any], target_language: str, output_dir: Path) -> dict[str, Any]:
    if translation.get("target_language") and str(translation["target_language"]).casefold() != target_language.casefold():
        raise ValueError("translation target_language does not match the requested language")
    supplied = translation.get("segments")
    if not isinstance(supplied, list):
        raise ValueError("translation segments must be a list")
    by_id: dict[int, str] = {}
    for item in supplied:
        if not isinstance(item, dict) or not isinstance(item.get("segment_id"), int) or not str(item.get("text") or "").strip():
            raise ValueError("every translated segment requires integer segment_id and non-empty text")
        if item["segment_id"] in by_id:
            raise ValueError(f"duplicate translated segment_id: {item['segment_id']}")
        by_id[item["segment_id"]] = str(item["text"]).strip()
    source_segments = [item for item in transcript.get("segments", []) if isinstance(item, dict)]
    source_ids = [item.get("segment_id") for item in source_segments]
    if set(by_id) != set(source_ids):
        missing = sorted(set(source_ids) - set(by_id))
        extra = sorted(set(by_id) - set(source_ids))
        raise ValueError(f"translation segment coverage mismatch; missing={missing}, extra={extra}")
    translated_segments = []
    for item in source_segments:
        segment_id = item["segment_id"]
        translated_segments.append({**item, "source_text": item.get("text"), "text": by_id[segment_id], "language": target_language})
    document = {
        "schema_version": "2.0", "created_at": datetime.now(timezone.utc).isoformat(),
        "method": "agent_or_provider_translation", "target_language": target_language,
        "source_file": transcript.get("source_file") or "transcript.json",
        "language": target_language, "source_language": transcript.get("language"), "segment_count": len(translated_segments),
        "timed_segment_count": sum(item.get("start_seconds") is not None for item in translated_segments),
        "speakers": transcript.get("speakers", []), "segments": translated_segments,
    }
    slug = language_slug(target_language)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"transcript.{slug}.json"
    md_path = output_dir / f"transcript.{slug}.md"
    srt_path = output_dir / f"transcript.{slug}.srt"
    vtt_path = output_dir / f"transcript.{slug}.vtt"
    atomic_write_json(json_path, document)
    write_markdown(document, md_path)
    written = [json_path, md_path]
    if write_srt(document, srt_path):
        written.append(srt_path)
    if write_vtt(document, vtt_path):
        written.append(vtt_path)
    return {"status": "translated", "target_language": target_language, "segments": len(translated_segments), "outputs": [str(path) for path in written]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript")
    parser.add_argument("--target-language", required=True)
    parser.add_argument("--translations", help="Completed provider/Agent JSON; omit to create a translation request")
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    transcript_path = Path(args.transcript).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else transcript_path.parent / "translations"
    try:
        transcript = load_object(transcript_path)
        if args.translations:
            result = apply_translation(transcript, load_object(Path(args.translations).expanduser().resolve()), args.target_language, output_dir)
            code = 0
        else:
            output_dir.mkdir(parents=True, exist_ok=True)
            request = output_dir / f"translation-request.{language_slug(args.target_language)}.json"
            result = create_request(transcript, args.target_language, request)
            code = 3
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return code
    except Exception as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
