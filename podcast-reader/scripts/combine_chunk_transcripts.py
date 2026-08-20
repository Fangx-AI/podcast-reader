#!/usr/bin/env python3
"""Combine timestamped chunk transcripts onto the episode's global timeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from normalize_transcript import parse_json_data
from runtime_utils import atomic_write_json, load_json_object


def combine(manifest_path: Path, transcript_dir: Path, allow_partial: bool = False) -> dict[str, Any]:
    manifest = load_json_object(manifest_path)
    if not manifest or not isinstance(manifest.get("chunks"), list) or (manifest.get("schema_version") == "2.0" and manifest.get("status") != "complete"):
        raise ValueError("audio chunk manifest is missing, invalid, or incomplete")
    combined: list[dict[str, Any]] = []
    missing: list[str] = []
    for chunk in manifest.get("chunks", []):
        audio = Path(chunk["file"])
        transcript = transcript_dir / f"{audio.stem}.transcript.json"
        if not transcript.is_file():
            missing.append(str(transcript))
            continue
        document = load_json_object(transcript)
        if not document:
            raise ValueError(f"invalid transcript JSON: {transcript}")
        if document.get("provider") == "local:faster-whisper" and document.get("status") != "complete":
            raise ValueError(f"incomplete local transcript cache: {transcript}")
        segments = parse_json_data(document)
        offset = float(chunk.get("global_offset_seconds") or 0)
        for item in segments:
            start = item.get("start_seconds")
            end = item.get("end_seconds")
            combined.append({
                "start_seconds": round(float(start) + offset, 6) if start is not None else None,
                "end_seconds": round(float(end) + offset, 6) if end is not None else None,
                "speaker": item.get("speaker"),
                "language": item.get("language"),
                "confidence": item.get("confidence"),
                "text": item.get("text"),
                "chunk_sequence": chunk.get("sequence"),
            })
    if missing and not allow_partial:
        raise FileNotFoundError("missing chunk transcripts: " + "; ".join(missing))
    if not combined:
        raise ValueError("no timestamped transcript segments found")
    return {
        "schema_version": "2.0",
        "status": "partial" if missing else "complete",
        "source_manifest": manifest_path.name,
        "completed_chunks": len(manifest.get("chunks", [])) - len(missing),
        "total_chunks": len(manifest.get("chunks", [])),
        "missing_transcripts": [Path(item).name for item in missing],
        "segments": combined,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--transcript-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-partial", action="store_true", help="Write available completed chunk transcripts without requiring every chunk")
    args = parser.parse_args()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    result = combine(Path(args.manifest).expanduser().resolve(), Path(args.transcript_dir).expanduser().resolve(), args.allow_partial)
    atomic_write_json(output, result)
    print(json.dumps({"output": str(output), "segment_count": len(result["segments"])}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
