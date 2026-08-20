#!/usr/bin/env python3
"""Combine timestamped chunk transcripts onto the episode's global timeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from normalize_transcript import parse_json_data


def combine(manifest_path: Path, transcript_dir: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    combined: list[dict[str, Any]] = []
    missing: list[str] = []
    for chunk in manifest.get("chunks", []):
        audio = Path(chunk["file"])
        transcript = transcript_dir / f"{audio.stem}.transcript.json"
        if not transcript.is_file():
            missing.append(str(transcript))
            continue
        segments = parse_json_data(json.loads(transcript.read_text(encoding="utf-8-sig")))
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
    if missing:
        raise FileNotFoundError("missing chunk transcripts: " + "; ".join(missing))
    if not combined:
        raise ValueError("no timestamped transcript segments found")
    return {
        "schema_version": "1.0",
        "source_manifest": str(manifest_path.resolve()),
        "segments": combined,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--transcript-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    result = combine(Path(args.manifest).expanduser().resolve(), Path(args.transcript_dir).expanduser().resolve())
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(output), "segment_count": len(result["segments"])}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
