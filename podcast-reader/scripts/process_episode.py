#!/usr/bin/env python3
"""Prepare, locally transcribe when needed, normalize, and index one episode."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".opus", ".flac", ".webm", ".mp4", ".mkv", ".mov"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_json(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def run_helper(name: str, arguments: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / name), *arguments],
        text=True, stdout=subprocess.PIPE, stderr=None,
        encoding="utf-8", errors="replace",
    )
    payload = parse_json(result.stdout)
    if result.returncode != 0:
        detail = payload.get("error") if payload else result.stdout[-2000:]
        raise RuntimeError(f"{name} failed ({result.returncode}): {detail or 'see progress output'}")
    if not payload:
        raise RuntimeError(f"{name} returned no JSON result")
    return payload


class Progress:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.path: Path | None = None

    def set_episode_dir(self, episode_dir: Path) -> None:
        self.path = episode_dir / "progress.json"
        self.flush()

    def emit(self, stage: str, status: str, message: str) -> None:
        event = {"at": now(), "stage": stage, "status": status, "message": message}
        self.events.append(event)
        print(f"[podcast-reader] {stage}: {message}", file=sys.stderr, flush=True)
        self.flush()

    def flush(self) -> None:
        if self.path:
            self.path.write_text(json.dumps({"schema_version": "1.0", "events": self.events}, ensure_ascii=False, indent=2), encoding="utf-8")


def media_files(bundle: dict[str, Any], episode_dir: Path) -> list[Path]:
    ingest_path = episode_dir / "ingest-result.json"
    candidates: list[str] = []
    if ingest_path.is_file():
        ingest = json.loads(ingest_path.read_text(encoding="utf-8-sig"))
        files = ingest.get("files") if isinstance(ingest.get("files"), dict) else {}
        candidates.extend(files.get("audio") or files.get("media") or [])
    resolution = bundle.get("resolution") if isinstance(bundle.get("resolution"), dict) else {}
    if resolution.get("kind") == "local_media" and resolution.get("path"):
        candidates.append(str(resolution["path"]))
    for relative in (bundle.get("artifacts") or {}).get("media", []):
        candidates.append(str(episode_dir / relative))

    found: list[Path] = []
    seen: set[Path] = set()
    for value in candidates:
        path = Path(value).expanduser()
        path = path if path.is_absolute() else episode_dir / path
        path = path.resolve()
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS and "audio-chunks" not in path.parts and path not in seen:
            found.append(path)
            seen.add(path)
    return found


def process(args: argparse.Namespace, progress: Progress) -> dict[str, Any]:
    progress.emit("prepare", "running", "Resolving source and acquiring the lightest usable evidence")
    prepare_args = [args.input, "--output-root", args.output_root, "--mode", args.acquire_mode, "--languages", args.languages]
    if args.output_dir:
        prepare_args.extend(["--output-dir", args.output_dir])
    if args.query:
        prepare_args.extend(["--query", args.query])
    if args.latest:
        prepare_args.append("--latest")
    if args.refresh:
        prepare_args.append("--refresh")
    bundle = run_helper("prepare_episode.py", prepare_args)
    episode_dir = Path(bundle["episode_dir"]).resolve()
    progress.set_episode_dir(episode_dir)
    progress.emit("prepare", "complete", f"Bundle status: {bundle.get('status')}")

    if bundle.get("status") in {"ready_for_analysis", "analyzed"}:
        return {"status": bundle["status"], "episode_dir": str(episode_dir), "bundle": str(episode_dir / "bundle.json"), "progress": str(progress.path), "api_key_required": False}
    if bundle.get("status") != "needs_transcription" or args.no_transcribe:
        progress.emit("transcription", "skipped", "No automatic local transcription was run")
        return {"status": bundle.get("status"), "episode_dir": str(episode_dir), "bundle": str(episode_dir / "bundle.json"), "progress": str(progress.path), "next_actions": bundle.get("next_actions", [])}

    media = media_files(bundle, episode_dir)
    if not media:
        raise RuntimeError("bundle needs transcription but no acquired/local media file was found")

    chunks_dir = episode_dir / "audio-chunks"
    progress.emit("chunking", "running", f"Preparing resumable audio chunks from {len(media)} source file(s)")
    chunk_args = [*[str(path) for path in media], "--output-dir", str(chunks_dir), "--segment-minutes", str(args.segment_minutes)]
    if args.force:
        chunk_args.append("--force")
    manifest = run_helper("prepare_audio_chunks.py", chunk_args)
    chunks = [Path(item["file"]) for item in manifest.get("chunks", [])]
    if not chunks:
        raise RuntimeError("audio chunk manifest contains no chunks")
    progress.emit("chunking", "complete", f"Prepared {len(chunks)} resumable chunk(s)")

    transcript_dir = episode_dir / "chunk-transcripts"
    progress.emit("transcription", "running", f"Local {args.model} transcription; completed chunks will be reused")
    transcription_args = [
        *[str(path) for path in chunks], "--output-dir", str(transcript_dir),
        "--model", args.model, "--language", args.language,
        "--beam-size", str(args.beam_size), "--batch-size", str(args.batch_size),
    ]
    if not args.no_bootstrap:
        transcription_args.append("--bootstrap")
    if args.force:
        transcription_args.append("--force")
    run_helper("transcribe_local.py", transcription_args)
    progress.emit("transcription", "complete", f"Transcribed or reused {len(chunks)} chunk(s)")

    combined = episode_dir / "transcript-combined.json"
    progress.emit("timeline", "running", "Restoring the episode-global timeline")
    run_helper("combine_chunk_transcripts.py", [
        str(chunks_dir / "audio-chunks.json"), "--transcript-dir", str(transcript_dir), "--output", str(combined),
    ])
    progress.emit("timeline", "complete", "Combined timestamped transcript")

    progress.emit("index", "running", "Normalizing transcript and building the follow-up index")
    bundle = run_helper("prepare_episode.py", [
        args.input, "--output-dir", str(episode_dir), "--transcript", str(combined), "--transcript-method", "generated",
    ])
    progress.emit("index", "complete", f"Bundle status: {bundle.get('status')}")
    return {
        "status": bundle.get("status"),
        "episode_dir": str(episode_dir),
        "bundle": str(episode_dir / "bundle.json"),
        "transcript": str(episode_dir / "transcript.json"),
        "chunks": str(episode_dir / "chunks.json"),
        "progress": str(progress.path),
        "api_key_required": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--output-root", default="outputs/podcast-reader")
    parser.add_argument("--output-dir")
    parser.add_argument("--query")
    parser.add_argument("--latest", action="store_true")
    parser.add_argument("--languages", default="zh-Hans,zh-Hant,zh-CN,zh-TW,zh,en,ja,ko")
    parser.add_argument("--acquire-mode", choices=("auto", "metadata", "subtitles", "audio", "video", "all"), default="auto")
    parser.add_argument("--model", default="small")
    parser.add_argument("--language", default="auto")
    parser.add_argument("--beam-size", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--segment-minutes", type=float, default=30.0)
    parser.add_argument("--no-bootstrap", action="store_true")
    parser.add_argument("--no-transcribe", action="store_true", help="Stop after acquisition when a transcript is unavailable")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--force", action="store_true", help="Recreate chunks and local transcripts")
    args = parser.parse_args()
    if args.beam_size < 1 or args.batch_size < 0 or args.segment_minutes <= 0:
        parser.error("beam size and segment minutes must be positive; batch size cannot be negative")
    progress = Progress()
    try:
        result = process(args, progress)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("status") not in {"blocked"} else 2
    except Exception as exc:
        progress.emit("pipeline", "failed", str(exc))
        print(json.dumps({"status": "blocked", "stage": "pipeline", "error": str(exc), "api_key_required": False}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
