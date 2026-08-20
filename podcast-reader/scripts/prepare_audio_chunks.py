#!/usr/bin/env python3
"""Split long audio into API-safe speech chunks with a global time-offset manifest."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, encoding="utf-8", errors="replace")


def duration_seconds(path: Path) -> float:
    result = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"ffprobe failed for {path}")
    return float(result.stdout.strip())


def split_audio(
    inputs: list[Path], output_dir: Path, segment_seconds: float, bitrate_kbps: int,
    max_bytes: int, force: bool,
) -> dict[str, Any]:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg and ffprobe are required")
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks: list[dict[str, Any]] = []
    global_offset = 0.0

    for source_index, source in enumerate(inputs, start=1):
        source = source.expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        pattern = output_dir / f"source-{source_index:02d}-chunk-%03d.ogg"
        existing = sorted(output_dir.glob(f"source-{source_index:02d}-chunk-*.ogg"))
        if force or not existing:
            overwrite = "-y" if force else "-n"
            result = run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", overwrite,
                "-i", str(source), "-vn", "-ac", "1", "-ar", "16000",
                "-c:a", "libopus", "-b:a", f"{bitrate_kbps}k",
                "-f", "segment", "-segment_time", str(segment_seconds),
                "-reset_timestamps", "1", str(pattern),
            ])
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or f"ffmpeg split failed for {source}")
            existing = sorted(output_dir.glob(f"source-{source_index:02d}-chunk-*.ogg"))
        if not existing:
            raise RuntimeError(f"no chunks produced for {source}")

        source_elapsed = 0.0
        for source_chunk_index, chunk in enumerate(existing, start=1):
            size = chunk.stat().st_size
            if size > max_bytes:
                raise RuntimeError(
                    f"chunk exceeds byte limit ({size} > {max_bytes}): {chunk}; "
                    "reduce --segment-minutes or --bitrate-kbps"
                )
            chunk_duration = duration_seconds(chunk)
            chunks.append({
                "sequence": len(chunks) + 1,
                "source_index": source_index,
                "source_chunk_index": source_chunk_index,
                "source_file": str(source),
                "file": str(chunk.resolve()),
                "source_offset_seconds": round(source_elapsed, 6),
                "global_offset_seconds": round(global_offset + source_elapsed, 6),
                "duration_seconds": round(chunk_duration, 6),
                "size_bytes": size,
            })
            source_elapsed += chunk_duration
        global_offset += duration_seconds(source)

    manifest = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "encoding": {"container": "ogg", "codec": "opus", "sample_rate": 16000, "channels": 1, "bitrate_kbps": bitrate_kbps},
        "segment_seconds": segment_seconds,
        "max_bytes": max_bytes,
        "total_duration_seconds": round(global_offset, 6),
        "chunks": chunks,
    }
    (output_dir / "audio-chunks.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", nargs="+", help="Ordered input audio files")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--segment-minutes", type=float, default=30.0)
    parser.add_argument("--bitrate-kbps", type=int, default=24)
    parser.add_argument("--max-bytes", type=int, default=24 * 1024 * 1024)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.segment_minutes <= 0 or args.bitrate_kbps <= 0 or args.max_bytes <= 0:
        parser.error("segment, bitrate, and byte limits must be positive")
    manifest = split_audio(
        [Path(value) for value in args.audio], Path(args.output_dir).expanduser().resolve(),
        args.segment_minutes * 60, args.bitrate_kbps, args.max_bytes, args.force,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
