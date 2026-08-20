#!/usr/bin/env python3
"""Split long audio into verified, transactionally resumable speech chunks."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any
import uuid

from runtime_utils import atomic_write_json, file_fingerprint, load_json_object, same_fingerprint


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, encoding="utf-8", errors="replace")


def duration_seconds(path: Path) -> float:
    result = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"ffprobe failed for {path}")
    value = float(result.stdout.strip())
    if value <= 0:
        raise RuntimeError(f"media duration is not positive: {path}")
    return value


def source_descriptor(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    return {
        "source_file": str(path),
        "fingerprint": file_fingerprint(path),
        "duration_seconds": round(duration_seconds(path), 6),
    }


def _coverage_ok(actual: float, expected: float) -> bool:
    return abs(actual - expected) <= max(2.0, expected * 0.005)


def validate_cached_manifest(
    manifest: dict[str, Any] | None,
    sources: list[dict[str, Any]],
    output_dir: Path,
    segment_seconds: float,
    bitrate_kbps: int,
    max_bytes: int,
    overlap_seconds: float = 1.5,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "2.0":
        return False, ["manifest_missing_or_legacy"]
    settings = manifest.get("settings") if isinstance(manifest.get("settings"), dict) else {}
    expected_settings = {"segment_seconds": segment_seconds, "bitrate_kbps": bitrate_kbps, "max_bytes": max_bytes, "overlap_seconds": overlap_seconds}
    if settings != expected_settings:
        reasons.append("settings_changed")
    cached_sources = manifest.get("sources") if isinstance(manifest.get("sources"), list) else []
    if len(cached_sources) != len(sources):
        reasons.append("source_count_changed")
    else:
        for cached, current in zip(cached_sources, sources):
            fingerprint = cached.get("fingerprint") if isinstance(cached, dict) else None
            if not same_fingerprint(fingerprint, current["fingerprint"]):
                reasons.append("source_fingerprint_changed")
                break
    chunks = manifest.get("chunks") if isinstance(manifest.get("chunks"), list) else []
    if not chunks:
        reasons.append("chunks_missing")
    if [item.get("sequence") for item in chunks if isinstance(item, dict)] != list(range(1, len(chunks) + 1)):
        reasons.append("chunk_sequence_not_contiguous")
    intervals: dict[int, list[tuple[float, float]]] = {}
    indexes_by_source: dict[int, list[int]] = {}
    for item in chunks:
        if not isinstance(item, dict):
            reasons.append("chunk_record_invalid")
            continue
        source_index = item.get("source_index")
        chunk_index = item.get("source_chunk_index")
        relative = item.get("relative_file")
        candidate = output_dir / relative if isinstance(relative, str) else Path(str(item.get("file") or ""))
        if not candidate.is_file() or candidate.stat().st_size <= 0:
            reasons.append("chunk_file_missing_or_empty")
            continue
        if candidate.stat().st_size > max_bytes:
            reasons.append("chunk_exceeds_limit")
        if not isinstance(source_index, int) or not isinstance(chunk_index, int):
            reasons.append("chunk_index_invalid")
            continue
        indexes_by_source.setdefault(source_index, []).append(chunk_index)
        start = float(item.get("source_offset_seconds") or 0)
        intervals.setdefault(source_index, []).append((start, start + float(item.get("duration_seconds") or 0)))
    for index, source in enumerate(sources, start=1):
        indexes = sorted(indexes_by_source.get(index, []))
        if indexes != list(range(1, len(indexes) + 1)):
            reasons.append(f"source_{index}_chunks_not_contiguous")
        ranges = sorted(intervals.get(index, []))
        complete = bool(ranges) and ranges[0][0] <= 0.5 and ranges[-1][1] >= float(source["duration_seconds"]) - 2
        complete = complete and all(current[0] <= previous[1] + 0.5 for previous, current in zip(ranges, ranges[1:]))
        if not complete:
            reasons.append(f"source_{index}_coverage_incomplete")
    return not reasons, list(dict.fromkeys(reasons))


def _promote_chunks(output_dir: Path, staged_files: list[Path]) -> None:
    token = uuid.uuid4().hex[:10]
    backups: list[tuple[Path, Path]] = []
    promoted: list[Path] = []
    try:
        for old in sorted(output_dir.glob("source-*-chunk-*.ogg")):
            backup = output_dir / f".{old.name}.old-{token}"
            old.replace(backup)
            backups.append((backup, old))
        for staged in staged_files:
            target = output_dir / staged.name
            staged.replace(target)
            promoted.append(target)
    except Exception:
        for target in promoted:
            target.unlink(missing_ok=True)
        for backup, original in backups:
            if backup.exists():
                backup.replace(original)
        raise
    for backup, _ in backups:
        backup.unlink(missing_ok=True)


def split_audio(
    inputs: list[Path], output_dir: Path, segment_seconds: float, bitrate_kbps: int,
    max_bytes: int, force: bool, overlap_seconds: float = 1.5,
) -> dict[str, Any]:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg and ffprobe are required")
    output_dir.mkdir(parents=True, exist_ok=True)
    resolved_inputs = [path.expanduser().resolve() for path in inputs]
    for source in resolved_inputs:
        if not source.is_file():
            raise FileNotFoundError(source)
    sources = [source_descriptor(source) for source in resolved_inputs]
    manifest_path = output_dir / "audio-chunks.json"
    cached = load_json_object(manifest_path)
    cache_valid, cache_reasons = validate_cached_manifest(cached, sources, output_dir, segment_seconds, bitrate_kbps, max_bytes, overlap_seconds)
    if cache_valid and not force:
        result = dict(cached or {})
        result["cache"] = "reused_verified"
        result["cache_validation"] = {"valid": True, "reasons": []}
        return result

    chunks: list[dict[str, Any]] = []
    global_offset = 0.0
    with tempfile.TemporaryDirectory(prefix=".chunks-build-", dir=output_dir) as temporary_folder:
        staging = Path(temporary_folder)
        for source_index, (source, descriptor) in enumerate(zip(resolved_inputs, sources), start=1):
            source_duration = float(descriptor["duration_seconds"])
            chunk_count = max(1, math.ceil(source_duration / segment_seconds))
            staged = []
            offsets = []
            for chunk_number in range(chunk_count):
                nominal_start = chunk_number * segment_seconds
                actual_start = max(0.0, nominal_start - (overlap_seconds if chunk_number else 0.0))
                actual_end = min(source_duration, (chunk_number + 1) * segment_seconds)
                target = staging / f"source-{source_index:02d}-chunk-{chunk_number:03d}.ogg"
                result = run([
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(actual_start), "-i", str(source),
                    "-t", str(max(0.01, actual_end - actual_start)), "-vn", "-ac", "1", "-ar", "16000",
                    "-c:a", "libopus", "-b:a", f"{bitrate_kbps}k", str(target),
                ])
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.strip() or f"ffmpeg split failed for {source}")
                staged.append(target)
                offsets.append(actual_start)
            if not staged:
                raise RuntimeError(f"no chunks produced for {source}")
            coverage_end = 0.0
            for source_chunk_index, (chunk, source_offset) in enumerate(zip(staged, offsets), start=1):
                size = chunk.stat().st_size
                if size <= 0 or size > max_bytes:
                    raise RuntimeError(f"invalid chunk size ({size} bytes): {chunk.name}")
                chunk_duration = duration_seconds(chunk)
                relative_file = chunk.name
                chunks.append({
                    "sequence": len(chunks) + 1,
                    "source_index": source_index,
                    "source_chunk_index": source_chunk_index,
                    "source_file": str(source),
                    "file": str((output_dir / relative_file).resolve()),
                    "relative_file": relative_file,
                    "source_offset_seconds": round(source_offset, 6),
                    "global_offset_seconds": round(global_offset + source_offset, 6),
                    "duration_seconds": round(chunk_duration, 6),
                    "size_bytes": size,
                    "sha256": file_fingerprint(chunk)["sha256"],
                })
                coverage_end = max(coverage_end, source_offset + chunk_duration)
            expected = float(descriptor["duration_seconds"])
            if coverage_end < expected - 2:
                raise RuntimeError(f"chunk coverage incomplete for {source.name}: {coverage_end:.3f}s of {expected:.3f}s")
            global_offset += expected
        _promote_chunks(output_dir, sorted(staging.glob("source-*-chunk-*.ogg")))

    manifest = {
        "schema_version": "2.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete",
        "cache": "rebuilt" if cached else "created",
        "cache_validation": {"valid": cache_valid, "reasons": cache_reasons},
        "encoding": {"container": "ogg", "codec": "opus", "sample_rate": 16000, "channels": 1},
        "settings": {"segment_seconds": segment_seconds, "bitrate_kbps": bitrate_kbps, "max_bytes": max_bytes, "overlap_seconds": overlap_seconds},
        "sources": sources,
        "total_duration_seconds": round(global_offset, 6),
        "chunks": chunks,
    }
    atomic_write_json(manifest_path, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", nargs="+", help="Ordered input audio files")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--segment-minutes", type=float, default=30.0)
    parser.add_argument("--bitrate-kbps", type=int, default=24)
    parser.add_argument("--max-bytes", type=int, default=24 * 1024 * 1024)
    parser.add_argument("--overlap-seconds", type=float, default=1.5, help="Speech context repeated before each chunk after the first")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.segment_minutes <= 0 or args.bitrate_kbps <= 0 or args.max_bytes <= 0 or args.overlap_seconds < 0 or args.overlap_seconds >= args.segment_minutes * 60:
        parser.error("segment, bitrate, and byte limits must be positive")
    manifest = split_audio(
        [Path(value) for value in args.audio], Path(args.output_dir).expanduser().resolve(),
        args.segment_minutes * 60, args.bitrate_kbps, args.max_bytes, args.force, args.overlap_seconds,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
