#!/usr/bin/env python3
"""Apply provider-neutral speaker turns to a timestamped transcript by overlap."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

from normalize_transcript import write_markdown, write_srt, write_vtt
from runtime_utils import atomic_write_json


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def turns_from(value: Any) -> list[dict[str, Any]]:
    items = value.get("segments") or value.get("turns") if isinstance(value, dict) else value
    if not isinstance(items, list):
        raise ValueError("diarization data must contain a segments/turns list")
    turns = []
    for item in items:
        if not isinstance(item, dict):
            continue
        start = item.get("start_seconds", item.get("start"))
        end = item.get("end_seconds", item.get("end"))
        speaker = item.get("speaker") or item.get("label")
        if isinstance(start, (int, float)) and isinstance(end, (int, float)) and end >= start and speaker:
            turns.append({"start": float(start), "end": float(end), "speaker": str(speaker)})
    if not turns:
        raise ValueError("no valid diarization turns found")
    return turns


def apply(transcript: dict[str, Any], turns: list[dict[str, Any]], min_overlap_ratio: float) -> dict[str, Any]:
    output_segments = []
    assigned = 0
    for item in transcript.get("segments", []):
        if not isinstance(item, dict):
            continue
        start = item.get("start_seconds")
        end = item.get("end_seconds")
        speaker = item.get("speaker")
        confidence = None
        if isinstance(start, (int, float)) and isinstance(end, (int, float)) and end >= start:
            overlaps: dict[str, float] = {}
            for turn in turns:
                overlap = max(0.0, min(float(end), turn["end"]) - max(float(start), turn["start"]))
                overlaps[turn["speaker"]] = overlaps.get(turn["speaker"], 0.0) + overlap
            if overlaps:
                candidate, overlap = max(overlaps.items(), key=lambda pair: pair[1])
                duration = max(0.001, float(end) - float(start))
                confidence = round(min(1.0, overlap / duration), 4)
                if confidence >= min_overlap_ratio:
                    speaker = candidate
                    assigned += 1
        output_segments.append({**item, "speaker": speaker, "speaker_confidence": confidence})
    speakers = sorted({str(item["speaker"]) for item in output_segments if item.get("speaker")})
    return {
        **transcript,
        "schema_version": "2.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "speaker_diarization": True,
        "speaker_count": len(speakers),
        "speakers": speakers,
        "segments": output_segments,
        "diarization_metrics": {"assigned_segments": assigned, "total_segments": len(output_segments), "coverage": round(assigned / len(output_segments), 4) if output_segments else 0.0},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript")
    parser.add_argument("diarization", help="JSON list or object with timestamped speaker turns")
    parser.add_argument("--output-dir")
    parser.add_argument("--min-overlap-ratio", type=float, default=0.35)
    args = parser.parse_args()
    if not 0 <= args.min_overlap_ratio <= 1:
        parser.error("--min-overlap-ratio must be between 0 and 1")
    try:
        transcript_path = Path(args.transcript).expanduser().resolve()
        output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else transcript_path.parent / "diarized"
        output_dir.mkdir(parents=True, exist_ok=True)
        document = apply(load(transcript_path), turns_from(load(Path(args.diarization).expanduser().resolve())), args.min_overlap_ratio)
        outputs = [output_dir / "transcript.diarized.json", output_dir / "transcript.diarized.md"]
        atomic_write_json(outputs[0], document)
        write_markdown(document, outputs[1])
        srt = output_dir / "transcript.diarized.srt"
        vtt = output_dir / "transcript.diarized.vtt"
        if write_srt(document, srt):
            outputs.append(srt)
        if write_vtt(document, vtt):
            outputs.append(vtt)
        print(json.dumps({"status": "diarized", "outputs": [str(path) for path in outputs], **document["diarization_metrics"]}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
