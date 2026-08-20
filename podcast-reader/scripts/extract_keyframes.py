#!/usr/bin/env python3
"""Extract bounded representative video frames and a contact sheet with FFmpeg."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

from runtime_utils import atomic_write_json


PTS_TIME = re.compile(r"pts_time:(\d+(?:\.\d+)?)")


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, text=True, capture_output=True, encoding="utf-8", errors="replace", timeout=60 * 60)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 124, "", "operation timed out after 60 minutes")


def probe_duration(video: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is not installed")
    result = run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video)])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe could not read video duration")
    return float(result.stdout.strip())


def display_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    whole = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{whole:02d}"


def extract_interval(ffmpeg: str, video: Path, output_dir: Path, duration: float, count: int, width: int) -> list[dict]:
    if duration <= 2:
        points = [max(0.0, duration / 2)]
    else:
        count = min(count, max(1, int(duration // 2)))
        points = [(index + 1) * duration / (count + 1) for index in range(count)]
    entries = []
    for index, seconds in enumerate(points, 1):
        target = output_dir / f"frame-{index:03d}.jpg"
        result = run([ffmpeg, "-hide_banner", "-loglevel", "error", "-ss", f"{seconds:.3f}", "-i", str(video), "-frames:v", "1", "-vf", f"scale={width}:-2", "-q:v", "2", "-y", str(target)])
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"failed to extract frame at {seconds:.3f}s")
        entries.append({"frame_id": index, "timestamp": display_time(seconds), "seconds": round(seconds, 3), "path": str(target.resolve()), "strategy": "interval"})
    return entries


def extract_scene(ffmpeg: str, video: Path, output_dir: Path, count: int, width: int, threshold: float) -> list[dict]:
    pattern = output_dir / "frame-%03d.jpg"
    filter_value = f"select='gt(scene,{threshold})',scale={width}:-2,showinfo"
    result = run([ffmpeg, "-hide_banner", "-i", str(video), "-vf", filter_value, "-vsync", "vfr", "-frames:v", str(count), "-q:v", "2", "-y", str(pattern)])
    files = sorted(output_dir.glob("frame-*.jpg"))
    timestamps = [float(value) for value in PTS_TIME.findall(result.stderr)]
    if result.returncode != 0 or not files:
        raise RuntimeError(result.stderr[-2000:] or "scene extraction produced no frames")
    entries = []
    for index, path in enumerate(files, 1):
        seconds = timestamps[index - 1] if index - 1 < len(timestamps) else 0.0
        entries.append({"frame_id": index, "timestamp": display_time(seconds), "seconds": round(seconds, 3), "path": str(path.resolve()), "strategy": "scene"})
    return entries


def make_contact_sheet(ffmpeg: str, output_dir: Path, count: int) -> Path | None:
    if count < 2:
        return None
    columns = min(4, count)
    rows = math.ceil(count / columns)
    target = output_dir / "contact-sheet.jpg"
    result = run([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-framerate", "1", "-start_number", "1",
        "-i", str(output_dir / "frame-%03d.jpg"), "-vf", f"scale=420:-2,tile={columns}x{rows}:padding=8:margin=8:color=white",
        "-frames:v", "1", "-q:v", "2", "-y", str(target),
    ])
    return target if result.returncode == 0 and target.exists() else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--strategy", choices=("interval", "scene"), default="interval")
    parser.add_argument("--max-frames", type=int, default=16)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--scene-threshold", type=float, default=0.35)
    args = parser.parse_args()
    if not 1 <= args.max_frames <= 60:
        raise ValueError("--max-frames must be between 1 and 60")

    video = Path(args.video).expanduser().resolve()
    if not video.is_file():
        raise FileNotFoundError(video)
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print(json.dumps({"status": "blocked", "stage": "dependency", "error": "ffmpeg is not installed"}, ensure_ascii=False), file=sys.stderr)
        return 2
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    duration = probe_duration(video)
    warnings = []
    try:
        if args.strategy == "scene":
            entries = extract_scene(ffmpeg, video, output_dir, args.max_frames, args.width, args.scene_threshold)
        else:
            entries = extract_interval(ffmpeg, video, output_dir, duration, args.max_frames, args.width)
    except RuntimeError as exc:
        if args.strategy != "scene":
            raise
        warnings.append(f"scene strategy failed and interval fallback was used: {exc}")
        entries = extract_interval(ffmpeg, video, output_dir, duration, args.max_frames, args.width)
    contact = make_contact_sheet(ffmpeg, output_dir, len(entries))
    manifest = {
        "schema_version": "1.0",
        "video": str(video),
        "duration_seconds": duration,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "frame_count": len(entries),
        "contact_sheet": str(contact.resolve()) if contact else None,
        "frames": entries,
        "warnings": warnings,
        "note": "Frame observations are visual evidence and must not be represented as spoken claims.",
    }
    manifest_path = output_dir / "manifest.json"
    atomic_write_json(manifest_path, manifest)
    print(json.dumps({"status": "ready", "manifest": str(manifest_path), "contact_sheet": manifest["contact_sheet"], "frame_count": len(entries), "warnings": warnings}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
