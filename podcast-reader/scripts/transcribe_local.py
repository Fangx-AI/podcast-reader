#!/usr/bin/env python3
"""Transcribe audio locally with faster-whisper; no API key is required."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any


PACKAGE_SPEC = "faster-whisper==1.2.1"
DEFAULT_MODEL = "small"


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
        "schema_version": "1.0",
        "provider": "local:faster-whisper",
        "model": args.model,
        "source_file": str(audio.resolve()),
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
    for index, audio in enumerate(audio_files, start=1):
        target = output_dir / f"{audio.stem}.transcript.json"
        if target.is_file() and not args.force:
            print(f"Reusing {index}/{len(audio_files)}: {target.name}", file=sys.stderr)
            outputs.append(str(target))
            continue
        print(f"Transcribing {index}/{len(audio_files)} locally: {audio.name}", file=sys.stderr)
        result = transcribe_one(inference, audio, args)
        result["device"] = device
        result["compute_type"] = compute_type
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append(str(target))
    print(json.dumps({"status": "ready", "api_key_required": False, "outputs": outputs}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
