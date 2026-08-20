#!/usr/bin/env python3
"""Inspect installed, bootstrap-capable, and offline-ready Podcast Reader capabilities."""

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
import tempfile
from typing import Any

from runtime_utils import skill_version


def command_check(name: str, version_args: list[str]) -> dict[str, Any]:
    executable = shutil.which(name)
    if not executable:
        return {"available": False, "path": None, "version": None}
    try:
        result = subprocess.run([executable, *version_args], text=True, capture_output=True, encoding="utf-8", errors="replace", timeout=10)
        lines = (result.stdout or result.stderr).strip().splitlines()
        return {"available": result.returncode == 0, "path": executable, "version": lines[0][:240] if lines else None}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "path": executable, "version": None, "error": str(exc)}


def nearest_existing_ancestor(path: Path) -> Path:
    candidate = path.expanduser().resolve()
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def writable_check(path: Path) -> dict[str, Any]:
    candidate = path.expanduser().resolve()
    ancestor = nearest_existing_ancestor(candidate)
    writable = False
    error: str | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".podcast-reader-write-test-", dir=ancestor, delete=True) as handle:
            handle.write(b"ok")
            handle.flush()
        writable = True
    except OSError as exc:
        error = str(exc)
    usage = shutil.disk_usage(ancestor)
    return {
        "path": str(candidate),
        "nearest_existing_ancestor": str(ancestor),
        "writable": writable,
        "write_test": "passed" if writable else "failed",
        "error": error,
        "free_bytes": usage.free,
        "free_gib": round(usage.free / (1024 ** 3), 2),
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
    media_installed = bool(commands["ffmpeg"]["available"] and commands["ffprobe"]["available"])
    transcription_installed = local_whisper
    ingestion_installed = bool(commands["yt-dlp"]["available"])
    bootstrap_capable = bool(commands["uv"]["available"])
    output = writable_check(output_root)
    core_ready = bool(python_ok and output["writable"])
    offline_ready = bool(core_ready and media_installed and transcription_installed and ingestion_installed)
    bootstrap_ready = bool(core_ready and media_installed and (transcription_installed or bootstrap_capable) and (ingestion_installed or bootstrap_capable))

    recommendations: list[str] = []
    if not python_ok:
        recommendations.append("Install Python 3.10 or newer.")
    if not output["writable"]:
        recommendations.append("Choose a writable --output-root.")
    if output["free_bytes"] < 5 * 1024 ** 3:
        recommendations.append("Keep at least 5 GiB free for long media, chunks, and local model weights.")
    if not media_installed:
        recommendations.append("Install FFmpeg and ensure ffmpeg/ffprobe are on PATH.")
    if not transcription_installed and bootstrap_capable:
        recommendations.append("Local transcription is bootstrap-capable, not installed; the first run needs network and downloads dependencies/model weights.")
    elif not transcription_installed:
        recommendations.append("Install faster-whisper or uv for zero-key local transcription.")
    if not ingestion_installed and bootstrap_capable:
        recommendations.append("yt-dlp is bootstrap-capable through uv, not installed; public platform ingestion may need network bootstrap.")
    elif not ingestion_installed:
        recommendations.append("Install yt-dlp or uv for public YouTube/Bilibili ingestion.")

    status = "ready" if offline_ready else "degraded" if bootstrap_ready or core_ready else "blocked"
    return {
        "schema_version": "2.0",
        "skill_version": skill_version(),
        "status": status,
        "readiness": "offline_ready" if offline_ready else "bootstrap_ready" if bootstrap_ready else "core_only" if core_ready else "blocked",
        "python": {"available": python_ok, "version": platform.python_version(), "implementation": platform.python_implementation(), "executable": sys.executable},
        "system": {"os": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "commands": commands,
        "python_packages": {"faster-whisper": {"available": local_whisper}},
        "output": output,
        "capabilities": {
            "transcript_and_index": core_ready,
            "media_processing_installed": media_installed,
            "platform_ingestion_installed": ingestion_installed,
            "local_transcription_installed": transcription_installed,
            "bootstrap_capable": bootstrap_capable,
            "full_pipeline_after_bootstrap": bootstrap_ready,
            "full_pipeline_offline_ready": offline_ready,
        },
        "api_key_required": False,
        "network_used": False,
        "recommendations": recommendations,
    }


def human(result: dict[str, Any]) -> str:
    mark = lambda value: "✓" if value else "–"
    caps = result["capabilities"]
    lines = [
        f"Podcast Reader {result['skill_version']}: {result['readiness']}",
        f"{mark(result['python']['available'])} Python {result['python']['version']}",
        f"{mark(caps['platform_ingestion_installed'])} Platform ingestion installed",
        f"{mark(caps['media_processing_installed'])} FFmpeg media processing installed",
        f"{mark(caps['local_transcription_installed'])} Local transcription installed",
        f"{mark(caps['bootstrap_capable'])} Network bootstrap available",
        f"{mark(result['output']['writable'])} Writable output ({result['output']['free_gib']} GiB free)",
    ]
    if result["recommendations"]:
        lines.append("Next:")
        lines.extend(f"- {item}" for item in result["recommendations"])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="outputs/podcast-reader")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--require-full", action="store_true", help="Exit nonzero unless the full pipeline is installed and offline-ready")
    args = parser.parse_args()
    result = inspect(Path(args.output_root))
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else human(result))
    if result["status"] == "blocked" or (args.require_full and result["readiness"] != "offline_ready"):
        return 2
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
