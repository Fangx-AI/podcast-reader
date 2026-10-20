#!/usr/bin/env python3
"""Create a privacy-sanitized, copyright-aware Podcast Reader ZIP export."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from typing import Any
import urllib.parse
import uuid
import zipfile

from runtime_utils import atomic_write_json, atomic_write_text, sha256_file, skill_version
from render_reader import render as render_reader
from validate_bundle import validate as validate_bundle


SENSITIVE_QUERY = re.compile(r"(?:token|sig(?:nature)?|auth|secret|session|jwt|key|policy|expires?|credential|hdnea)", re.I)
ABSOLUTE_PATH = re.compile(r"(?<![A-Za-z0-9])(?:(?:[A-Za-z]:[\\/])|/Users/|/home/)[^\s\"'<>]+")
# Escaped tag/quote delimiters belong to the surrounding HTML, not the URL.
# In particular, the hidden Markdown payload wraps link targets in &lt;/&gt;.
WEB_URL = re.compile(r"https?://(?:(?!&(?:lt|gt|quot|apos|#(?:\d+|x[0-9a-f]+));)[^\s\"'<>])+", re.I)
ALWAYS = {"bundle.json", "source.json", "source-info.json", "analysis.md", "summary.md", "evidence.json", "reader.html", "analysis-handoff.json"}
KNOWLEDGE = {"transcript.json", "transcript.md", "transcript.srt", "transcript.vtt", "chunks.json"}


def sanitized_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"}:
        return value
    query = [
        (key, item)
        for key, item in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if not SENSITIVE_QUERY.search(key)
        and not key.casefold().startswith("utm_") and key.casefold() not in {"fbclid", "gclid"}
    ]
    host = parsed.hostname or ""
    if ":" in host:
        host = f"[{host}]"
    port = f":{parsed.port}" if parsed.port else ""
    fragment = parsed.fragment
    if "=" in fragment:
        fragment = urllib.parse.urlencode([
            (key, item) for key, item in urllib.parse.parse_qsl(fragment, keep_blank_values=True)
            if not SENSITIVE_QUERY.search(key)
        ])
    return urllib.parse.urlunsplit((parsed.scheme, host + port, parsed.path, urllib.parse.urlencode(query), fragment))


def sanitize_value(value: Any, episode_dir: Path, key: str = "") -> Any:
    if isinstance(value, dict):
        return {item: sanitize_value(child, episode_dir, item) for item, child in value.items()}
    if isinstance(value, list):
        return [sanitize_value(child, episode_dir, key) for child in value]
    if not isinstance(value, str):
        return value
    if value.lower().startswith(("http://", "https://")) and not re.search(r"\s", value):
        return sanitized_url(value)
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(episode_dir).as_posix()
        except (ValueError, OSError):
            return f"[LOCAL_PATH_REDACTED]/{candidate.name}"
    return sanitize_text(value, episode_dir)


def sanitize_text(value: str, episode_dir: Path) -> str:
    # Protect web URLs before masking paths: "https:/" contains a drive-like
    # suffix, and legitimate web paths can themselves contain "/Users/".
    urls: list[str] = []
    prefix = f"\x00podcast-url-{uuid.uuid4().hex}-"

    def protect_url(match: re.Match[str]) -> str:
        original = match.group(0)
        core = original.rstrip(".,;!?}")
        for opening, closing in (("(", ")"), ("[", "]")):
            while core.endswith(closing) and core.count(closing) > core.count(opening):
                core = core[:-1]
        suffix = original[len(core):]
        escaped_html = "&amp;" in core.lower()
        # Decode only query separators. Unescaping quotes or angle brackets
        # here would turn already-safe HTML text back into active markup.
        cleaned = sanitized_url(re.sub(r"&amp;", "&", core, flags=re.I))
        if escaped_html:
            cleaned = html.escape(cleaned, quote=True)
        urls.append(cleaned + suffix)
        return f"{prefix}{len(urls) - 1}\x00"

    value = WEB_URL.sub(protect_url, value)
    root_forms = {str(episode_dir), str(episode_dir).replace("\\", "/")}
    for root in sorted(root_forms, key=len, reverse=True):
        value = value.replace(root, ".")
    value = ABSOLUTE_PATH.sub("[LOCAL_PATH_REDACTED]", value)
    for index, url in enumerate(urls):
        value = value.replace(f"{prefix}{index}\x00", url)
    return value


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
    bundle = json.loads((episode_dir / "bundle.json").read_text(encoding="utf-8-sig"))
    if profile in {"share", "portable"}:
        if not isinstance(bundle, dict) or bundle.get("status") != "analyzed":
            raise ValueError("Complete the summary with finalize_bundle.py before sharing or creating a portable export.")
        validation = validate_bundle(episode_dir)
        if not validation["valid"]:
            raise ValueError("The summary is incomplete or stale; run finalize_bundle.py first: " + "; ".join(validation["errors"]))
    files = selected_files(episode_dir, profile, include_full_transcript)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="podcast-reader-export-") as temporary_folder:
        staging = Path(temporary_folder) / "podcast-reader-bundle"
        staging.mkdir()
        for source in files:
            relative = source.relative_to(episode_dir)
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.name == "reader.html" and not include_full_transcript:
                # A collapsed transcript is still the complete text in the HTML.
                # Render the summary alone for the default share export.
                if not (episode_dir / "transcript.json").is_file():
                    raise FileNotFoundError("transcript.json is required to build an export without the embedded transcript.")
                render_reader(episode_dir, target, include_transcript=False)
                atomic_write_text(target, sanitize_text(target.read_text(encoding="utf-8"), episode_dir))
            elif source.suffix.lower() == ".json":
                try:
                    value = json.loads(source.read_text(encoding="utf-8-sig"))
                    atomic_write_json(target, sanitize_value(value, episode_dir))
                except (json.JSONDecodeError, UnicodeError):
                    atomic_write_text(target, sanitize_text(source.read_text(encoding="utf-8", errors="replace"), episode_dir))
            elif source.suffix.lower() in {".md", ".html", ".txt", ".vtt", ".srt", ".csv"}:
                atomic_write_text(target, sanitize_text(source.read_text(encoding="utf-8", errors="replace"), episode_dir))
            else:
                shutil.copy2(source, target)
        exported_bundle_path = staging / "bundle.json"
        exported_bundle = json.loads(exported_bundle_path.read_text(encoding="utf-8-sig"))
        if isinstance(exported_bundle, dict) and isinstance(exported_bundle.get("deliverable_hashes"), dict):
            exported_bundle["deliverable_hashes"] = {
                name: sha256_file(staging / name)
                for name in ("summary.md", "reader.html")
                if (staging / name).is_file()
            }
            atomic_write_json(exported_bundle_path, exported_bundle)
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
