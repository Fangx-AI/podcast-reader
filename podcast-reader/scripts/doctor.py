#!/usr/bin/env python3
"""Check Podcast Reader runtime capabilities without downloading anything."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any


def command_check(name: str, version_args: list[str]) -> dict[str, Any]:
    executable = shutil.which(name)
    if not executable:
        return {"available": False, "path": None, "version": None}
    try:
        result = subprocess.run(
            [executable, *version_args], text=True, capture_output=True,
            encoding="utf-8", errors="replace", timeout=10,
        )
        first_line = (result.stdout or result.stderr).strip().splitlines()
        version = first_line[0][:240] if first_line else None
        return {"available": result.returncode == 0, "path": executable, "version": version}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "path": executable, "version": None, "error": str(exc)}


def writable_check(path: Path) -> dict[str, Any]:
    candidate = path.expanduser().resolve()
    parent = candidate if candidate.exists() else candidate.parent
    return {
        "path": str(candidate),
        "parent_exists": parent.exists(),
        "writable": parent.exists() and os.access(parent, os.W_OK),
    }


def inspect(output_root: Path) -> dict[str, Any]:
    commands = {
        "ffmpeg": command_check("ffmpeg", ["-version"]),
        "ffprobe": command_check("ffprobe", ["-version"]),
        "uv": command_check("uv", ["--version"]),
        "yt-dlp": command_check("yt-dlp", ["--version"]),
    }
    python_ok = sys.version_info >= (3, 10)
    local_whisper = importlib.util.find_spec("faster_whisper") is not None
    media_ready = commands["ffmpeg"]["available"] and commands["ffprobe"]["available"]
    local_transcription_ready = local_whisper or commands["uv"]["available"]
    platform_ingestion_ready = commands["yt-dlp"]["available"] or commands["uv"]["available"]
    output = writable_check(output_root)
    core_ready = python_ok and output["writable"]
    full_zero_key_ready = core_ready and media_ready and local_transcription_ready and platform_ingestion_ready

    recommendations: list[str] = []
    if not python_ok:
        recommendations.append("Install Python 3.10 or newer.")
    if not output["writable"]:
        recommendations.append("Choose a writable --output-root.")
    if not media_ready:
        recommendations.append("Install FFmpeg and ensure ffmpeg/ffprobe are on PATH for media processing.")
    if not local_transcription_ready:
        recommendations.append("Install uv or faster-whisper for zero-key local transcription.")
    if not platform_ingestion_ready:
        recommendations.append("Install yt-dlp or uv for public YouTube/Bilibili ingestion.")

    return {
        "status": "ready" if full_zero_key_ready else ("degraded" if core_ready else "blocked"),
        "python": {
            "available": python_ok,
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
        },
        "system": {"os": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "commands": commands,
        "python_packages": {"faster-whisper": {"available": local_whisper}},
        "output": output,
        "capabilities": {
            "transcript_and_index": core_ready,
            "media_processing": media_ready,
            "platform_ingestion": platform_ingestion_ready,
            "zero_key_local_transcription": local_transcription_ready,
            "full_zero_key_pipeline": full_zero_key_ready,
        },
        "api_key_required": False,
        "network_used": False,
        "recommendations": recommendations,
    }


def human(result: dict[str, Any]) -> str:
    mark = lambda value: "✓" if value else "–"
    caps = result["capabilities"]
    lines = [
        f"Podcast Reader doctor: {result['status']}",
        f"{mark(result['python']['available'])} Python {result['python']['version']}",
        f"{mark(caps['platform_ingestion'])} Public platform ingestion",
        f"{mark(caps['media_processing'])} FFmpeg media processing",
        f"{mark(caps['zero_key_local_transcription'])} Zero-key local transcription",
        f"{mark(result['output']['writable'])} Writable output: {result['output']['path']}",
    ]
    if result["recommendations"]:
        lines.append("Next:")
        lines.extend(f"- {item}" for item in result["recommendations"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="outputs/podcast-reader")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--require-full", action="store_true", help="Exit nonzero unless the full zero-key pipeline is ready")
    args = parser.parse_args()
    result = inspect(Path(args.output_root))
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else human(result))
    if result["status"] == "blocked" or (args.require_full and result["status"] != "ready"):
        return 2
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
