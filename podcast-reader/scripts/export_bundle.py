#!/usr/bin/env python3
"""Create a privacy-sanitized, copyright-aware Podcast Reader ZIP export."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from typing import Any
import urllib.parse
import zipfile

from runtime_utils import atomic_write_json, atomic_write_text, sha256_file, skill_version


SENSITIVE_QUERY = re.compile(r"(?:token|sig(?:nature)?|auth|secret|session|jwt|key|policy|expires?|credential|hdnea)", re.I)
ABSOLUTE_PATH = re.compile(r"(?:(?:[A-Za-z]:[\\/])|/Users/|/home/)[^\s\"'<>]+")
ALWAYS = {"bundle.json", "source.json", "source-info.json", "analysis.md", "summary.md", "evidence.json", "reader.html", "analysis-handoff.json"}
KNOWLEDGE = {"transcript.json", "transcript.md", "transcript.srt", "transcript.vtt", "chunks.json"}


def sanitized_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        return value
    query = [
        (key, "[REDACTED]" if SENSITIVE_QUERY.search(key) else item)
        for key, item in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_") and key.casefold() not in {"fbclid", "gclid"}
    ]
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    return urllib.parse.urlunsplit((parsed.scheme, host + port, parsed.path, urllib.parse.urlencode(query), ""))


def sanitize_value(value: Any, episode_dir: Path, key: str = "") -> Any:
    if isinstance(value, dict):
        return {item: sanitize_value(child, episode_dir, item) for item, child in value.items()}
    if isinstance(value, list):
        return [sanitize_value(child, episode_dir, key) for child in value]
    if not isinstance(value, str):
        return value
    if value.startswith(("http://", "https://")):
        return sanitized_url(value)
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(episode_dir).as_posix()
        except (ValueError, OSError):
            return f"[LOCAL_PATH_REDACTED]/{candidate.name}"
    return value


def sanitize_text(value: str, episode_dir: Path) -> str:
    root_forms = {str(episode_dir), str(episode_dir).replace("\\", "/")}
    for root in sorted(root_forms, key=len, reverse=True):
        value = value.replace(root, ".")
    return ABSOLUTE_PATH.sub("[LOCAL_PATH_REDACTED]", value)


def selected_files(episode_dir: Path, profile: str, include_full_transcript: bool) -> list[Path]:
    files: set[Path] = set()
    for name in ALWAYS:
        path = episode_dir / name
        if path.is_file():
            files.add(path)
    for path in (episode_dir / "frames").rglob("*") if (episode_dir / "frames").is_dir() else []:
        if path.is_file():
            files.add(path)
    if profile in {"portable", "archive"} and include_full_transcript:
        for name in KNOWLEDGE:
            path = episode_dir / name
            if path.is_file():
                files.add(path)
        for path in (episode_dir / "translations").rglob("*") if (episode_dir / "translations").is_dir() else []:
            if path.is_file():
                files.add(path)
    if profile == "archive":
        for path in episode_dir.rglob("*"):
            if path.is_file() and path.suffix != ".part" and ".invalid-cache" not in path.parts:
                if include_full_transcript or not (path.name.startswith("transcript") or path.name == "chunks.json"):
                    files.add(path)
    return sorted(files)


def export(episode_dir: Path, output: Path, profile: str, include_full_transcript: bool) -> dict[str, Any]:
    episode_dir = episode_dir.expanduser().resolve()
    output = output.expanduser().resolve()
    if not (episode_dir / "bundle.json").is_file():
        raise FileNotFoundError("bundle.json is missing")
    files = selected_files(episode_dir, profile, include_full_transcript)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="podcast-reader-export-") as temporary_folder:
        staging = Path(temporary_folder) / "podcast-reader-bundle"
        staging.mkdir()
        for source in files:
            relative = source.relative_to(episode_dir)
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.suffix.lower() == ".json":
                try:
                    value = json.loads(source.read_text(encoding="utf-8-sig"))
                    atomic_write_json(target, sanitize_value(value, episode_dir))
                except (json.JSONDecodeError, UnicodeError):
                    atomic_write_text(target, sanitize_text(source.read_text(encoding="utf-8", errors="replace"), episode_dir))
            elif source.suffix.lower() in {".md", ".html", ".txt", ".vtt", ".srt", ".csv"}:
                atomic_write_text(target, sanitize_text(source.read_text(encoding="utf-8", errors="replace"), episode_dir))
            else:
                shutil.copy2(source, target)
        manifest_files = []
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                manifest_files.append({"path": path.relative_to(staging).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
        manifest = {
            "schema_version": "2.0", "skill_version": skill_version(), "created_at": datetime.now(timezone.utc).isoformat(),
            "profile": profile, "full_transcript_included": include_full_transcript,
            "privacy": "absolute local paths and sensitive URL query values sanitized",
            "copyright_note": "A full transcript is included only when explicitly requested after confirming rights or permitted use.",
            "files": manifest_files,
        }
        atomic_write_json(staging / "EXPORT-MANIFEST.json", manifest)
        temporary_zip = output.with_name(f".{output.name}.tmp")
        temporary_zip.unlink(missing_ok=True)
        with zipfile.ZipFile(temporary_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    archive.write(path, Path("podcast-reader-bundle") / path.relative_to(staging))
        os.replace(temporary_zip, output)
    return {"status": "exported", "profile": profile, "output": str(output), "sha256": sha256_file(output), "file_count": len(files) + 1, "full_transcript_included": include_full_transcript}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode_dir")
    parser.add_argument("--output")
    parser.add_argument("--profile", choices=("share", "portable", "archive"), default="share")
    parser.add_argument("--include-full-transcript", action="store_true", help="Include transcript/index only after confirming rights or permitted use")
    args = parser.parse_args()
    episode_dir = Path(args.episode_dir).expanduser().resolve()
    output = Path(args.output).expanduser().resolve() if args.output else episode_dir.with_name(f"{episode_dir.name}-{args.profile}.zip")
    try:
        result = export(episode_dir, output, args.profile, args.include_full_transcript)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
