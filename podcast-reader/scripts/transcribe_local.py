#!/usr/bin/env python3
"""Transcribe audio locally with faster-whisper; no API key is required."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any

from runtime_utils import atomic_write_json, file_fingerprint, load_json_object, same_fingerprint


PACKAGE_SPEC = "faster-whisper==1.2.1"
DEFAULT_MODEL = "small"


def cache_settings(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "provider": "local:faster-whisper",
        "package": PACKAGE_SPEC,
        "model": args.model,
        "language": args.language,
        "task": args.task,
        "beam_size": args.beam_size,
        "batch_size": args.batch_size,
        "word_timestamps": args.word_timestamps,
        "vad_filter": not args.no_vad,
    }


def valid_cached_transcript(target: Path, audio: Path, args: argparse.Namespace) -> tuple[bool, str]:
    document = load_json_object(target)
    if not document:
        return False, "invalid_json"
    if document.get("status") != "complete" or document.get("schema_version") != "2.0":
        return False, "legacy_or_incomplete"
    segments = document.get("segments")
    if not isinstance(segments, list) or not segments:
        return False, "segments_missing"
    if any(not isinstance(item, dict) or not str(item.get("text") or "").strip() for item in segments):
        return False, "segments_invalid"
    cache = document.get("cache") if isinstance(document.get("cache"), dict) else {}
    if cache.get("settings") != cache_settings(args):
        return False, "settings_changed"
    if not same_fingerprint(cache.get("source"), file_fingerprint(audio)):
        return False, "source_changed"
    return True, "verified"


def quarantine_invalid_cache(target: Path, reason: str) -> Path | None:
    if not target.exists():
        return None
    folder = target.parent / ".invalid-cache"
    folder.mkdir(parents=True, exist_ok=True)
    candidate = folder / f"{target.stem}.{reason}{target.suffix}"
    suffix = 1
    while candidate.exists():
        candidate = folder / f"{target.stem}.{reason}-{suffix}{target.suffix}"
        suffix += 1
    target.replace(candidate)
    return candidate


def write_progress(path: Path | None, completed: int, total: int, started: float, current: str | None = None) -> None:
    if not path:
        return
    elapsed = max(0.0, time.monotonic() - started)
    rate = completed / elapsed if completed and elapsed else 0.0
    remaining = total - completed
    atomic_write_json(path, {
        "schema_version": "2.0",
        "stage": "transcription",
        "status": "complete" if completed == total else "running",
        "completed_chunks": completed,
        "total_chunks": total,
        "percent": round(completed / total * 100, 1) if total else 100.0,
        "elapsed_seconds": round(elapsed, 1),
        "eta_seconds": round(remaining / rate, 1) if rate else None,
        "current": current,
        "partial_results_available": completed > 0,
    })


def write_partial_transcript(manifest: Path | None, transcript_dir: Path, output: Path | None) -> None:
    if not manifest or not output:
        return
    from combine_chunk_transcripts import combine
    partial = combine(manifest, transcript_dir, allow_partial=True)
    atomic_write_json(output, partial)


def bootstrap_with_uv() -> int:
    uv = shutil.which("uv")
    if not uv:
        print(json.dumps({
            "status": "blocked",
            "stage": "dependency",
            "error": "faster-whisper is not installed and uv is unavailable",
            "next_actions": [
                f"install {PACKAGE_SPEC} in an isolated Python 3.9+ environment",
                "rerun this command without --bootstrap",
            ],
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    child_args = [value for value in sys.argv[1:] if value != "--bootstrap"]
    command = [
        uv, "run", "--python", "3.12", "--with", PACKAGE_SPEC,
        "python", str(Path(__file__).resolve()), *child_args, "--_uv-child",
    ]
    return subprocess.run(command).returncode


def choose_device(requested: str) -> tuple[str, str]:
    if requested == "cpu":
        return "cpu", "int8"
    if requested == "cuda":
        return "cuda", "float16"
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def serialize_segment(segment: Any, include_words: bool) -> dict[str, Any]:
    item: dict[str, Any] = {
        "start": round(float(segment.start), 6),
        "end": round(float(segment.end), 6),
        "speaker": None,
        "text": str(segment.text).strip(),
        "confidence": round(max(0.0, min(1.0, math.exp(float(getattr(segment, "avg_logprob", -10.0))))), 6),
        "avg_logprob": getattr(segment, "avg_logprob", None),
        "no_speech_probability": getattr(segment, "no_speech_prob", None),
        "compression_ratio": getattr(segment, "compression_ratio", None),
    }
    if include_words and getattr(segment, "words", None):
        item["words"] = [
            {
                "start": round(float(word.start), 6) if word.start is not None else None,
                "end": round(float(word.end), 6) if word.end is not None else None,
                "word": str(word.word),
                "probability": getattr(word, "probability", None),
            }
            for word in segment.words
        ]
    return item


def transcribe_one(model: Any, audio: Path, args: argparse.Namespace) -> dict[str, Any]:
    options: dict[str, Any] = {
        "beam_size": args.beam_size,
        "vad_filter": not args.no_vad,
        "word_timestamps": args.word_timestamps,
        "task": args.task,
    }
    if getattr(args, "batch_size", 0) > 0:
        options["batch_size"] = args.batch_size
    if args.language and args.language != "auto":
        options["language"] = args.language
    segments, info = model.transcribe(str(audio), **options)
    materialized = [serialize_segment(segment, args.word_timestamps) for segment in segments]
    materialized = [item for item in materialized if item["text"]]
    return {
        "schema_version": "2.0",
        "status": "complete",
        "provider": "local:faster-whisper",
        "model": args.model,
        "source_file": audio.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "language": getattr(info, "language", None),
        "language_probability": getattr(info, "language_probability", None),
        "duration_seconds": getattr(info, "duration", None),
        "speaker_diarization": False,
        "segments": materialized,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", nargs="+", help="Ordered audio files or prepared audio chunks")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Whisper model size/name or local model path")
    parser.add_argument("--language", default="auto", help="ISO language hint or auto")
    parser.add_argument("--task", choices=("transcribe", "translate"), default="transcribe")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=0, help="Use batched inference when greater than zero")
    parser.add_argument("--word-timestamps", action="store_true")
    parser.add_argument("--no-vad", action="store_true")
    parser.add_argument("--model-cache", help="Optional model download/cache directory")
    parser.add_argument("--progress-json", help="Write per-chunk progress, elapsed time, and ETA to this JSON file")
    parser.add_argument("--chunk-manifest", help="Chunk manifest used to publish partial transcript results")
    parser.add_argument("--partial-output", help="Write a reusable partial combined transcript after each completed chunk")
    parser.add_argument("--bootstrap", action="store_true", help=f"Use uv to run with {PACKAGE_SPEC} when missing")
    parser.add_argument("--force", action="store_true", help="Overwrite existing transcript JSON instead of resuming")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--_uv-child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    audio_files = [Path(value).expanduser().resolve() for value in args.audio]
    missing = [str(path) for path in audio_files if not path.is_file()]
    if missing:
        parser.error("audio file not found: " + "; ".join(missing))
    output_dir = Path(args.output_dir).expanduser().resolve()
    plan = {
        "provider": "local:faster-whisper",
        "api_key_required": False,
        "package": PACKAGE_SPEC,
        "model": args.model,
        "language": args.language,
        "device": args.device,
        "inputs": [str(path) for path in audio_files],
        "output_dir": str(output_dir),
    }
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    try:
        from faster_whisper import BatchedInferencePipeline, WhisperModel
    except ImportError:
        if args.bootstrap and not args._uv_child:
            return bootstrap_with_uv()
        print(json.dumps({
            "status": "blocked",
            "stage": "dependency",
            "error": f"{PACKAGE_SPEC} is not installed",
            "next_actions": ["rerun with --bootstrap", f"or install {PACKAGE_SPEC} in an isolated environment"],
        }, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    device, compute_type = choose_device(args.device)
    model_options: dict[str, Any] = {"device": device, "compute_type": compute_type}
    if args.model_cache:
        model_options["download_root"] = str(Path(args.model_cache).expanduser().resolve())
    try:
        model = WhisperModel(args.model, **model_options)
    except Exception:
        if args.device == "auto" and device == "cuda":
            device, compute_type = "cpu", "int8"
            model_options.update({"device": device, "compute_type": compute_type})
            model = WhisperModel(args.model, **model_options)
        else:
            raise

    inference = BatchedInferencePipeline(model=model) if args.batch_size > 0 else model
    outputs = []
    reused = 0
    rebuilt = 0
    started = time.monotonic()
    progress_path = Path(args.progress_json).expanduser().resolve() if args.progress_json else None
    manifest_path = Path(args.chunk_manifest).expanduser().resolve() if args.chunk_manifest else None
    partial_output = Path(args.partial_output).expanduser().resolve() if args.partial_output else None
    write_progress(progress_path, 0, len(audio_files), started)
    for index, audio in enumerate(audio_files, start=1):
        target = output_dir / f"{audio.stem}.transcript.json"
        if target.is_file() and not args.force:
            valid, reason = valid_cached_transcript(target, audio, args)
            if valid:
                reused += 1
                percent = round(index / len(audio_files) * 100, 1)
                print(f"Reusing verified {index}/{len(audio_files)} ({percent}%): {target.name}", file=sys.stderr, flush=True)
                outputs.append(str(target))
                write_progress(progress_path, len(outputs), len(audio_files), started, target.name)
                write_partial_transcript(manifest_path, output_dir, partial_output)
                continue
            quarantined = quarantine_invalid_cache(target, reason)
            print(f"Discarded unsafe cache {target.name} ({reason}); preserved at {quarantined}", file=sys.stderr, flush=True)
        percent_before = round((index - 1) / len(audio_files) * 100, 1)
        print(f"Transcribing {index}/{len(audio_files)} ({percent_before}% complete): {audio.name}", file=sys.stderr, flush=True)
        result = transcribe_one(inference, audio, args)
        result["device"] = device
        result["compute_type"] = compute_type
        result["cache"] = {"source": file_fingerprint(audio), "settings": cache_settings(args)}
        if not result.get("segments"):
            raise RuntimeError(f"transcription produced no speech segments: {audio}")
        atomic_write_json(target, result)
        rebuilt += 1
        outputs.append(str(target))
        write_progress(progress_path, len(outputs), len(audio_files), started, target.name)
        write_partial_transcript(manifest_path, output_dir, partial_output)
    print(json.dumps({
        "status": "ready", "api_key_required": False, "outputs": outputs,
        "completed": len(outputs), "total": len(audio_files), "reused": reused, "transcribed": rebuilt,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
