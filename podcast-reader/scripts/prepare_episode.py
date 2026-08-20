#!/usr/bin/env python3
"""One-command episode preparation: resolve, acquire, normalize, index, manifest."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from resolve_podcast import resolve_input
from runtime_utils import atomic_write_json, safe_urlopen


SCRIPT_DIR = Path(__file__).resolve().parent
TRANSCRIPT_EXTENSIONS = {".srt", ".vtt", ".txt", ".md", ".json", ".json3", ".ass", ".ttml", ".lrc"}
MEDIA_EXTENSIONS = {".mp3", ".m4a", ".mp4", ".wav", ".aac", ".ogg", ".opus", ".flac", ".webm", ".mkv", ".mov"}
SENSITIVE_QUERY = re.compile(r"(?:token|sig(?:nature)?|auth|secret|session|jwt|key|policy|expires?|credential|hdnea)", re.I)


def slugify(value: str, fallback: str = "episode") -> str:
    value = re.sub(r"[<>:\"/\\|?*\x00-\x1f]+", "-", value, flags=re.UNICODE)
    value = re.sub(r"\s+", "-", value).strip(" .-")
    return value[:90] or fallback


def source_key(value: str) -> str:
    local = Path(value).expanduser()
    if local.exists():
        stat = local.stat()
        identity = f"{local.resolve()}|{stat.st_size}|{stat.st_mtime_ns}"
    else:
        parsed = urllib.parse.urlsplit(value.strip())
        host = parsed.netloc.casefold().split(":", 1)[0]
        query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if host == "youtu.be":
            query = []
        elif host.endswith("youtube.com"):
            query = [(key, item) for key, item in query if key == "v"]
        elif host == "b23.tv" or host.endswith("bilibili.com"):
            query = [(key, item) for key, item in query if key == "p"]
        else:
            query = [(key, item) for key, item in query if not key.casefold().startswith("utm_") and key.casefold() not in {"fbclid", "gclid"}]
        identity = urllib.parse.urlunsplit((parsed.scheme.casefold(), parsed.netloc.casefold(), parsed.path.rstrip("/"), urllib.parse.urlencode(query), ""))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]


def sanitize_url(value: str, strip_query: bool = False) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        return value
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    query = [] if strip_query else [
        (key, "[REDACTED]" if SENSITIVE_QUERY.search(key) else item)
        for key, item in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    ]
    return urllib.parse.urlunsplit((parsed.scheme, host + port, parsed.path, urllib.parse.urlencode(query), ""))


def sanitize_for_storage(value: Any, key: str = "") -> Any:
    if isinstance(value, dict):
        return {item_key: sanitize_for_storage(item_value, item_key) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [sanitize_for_storage(item, key) for item in value]
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        media_context = any(term in key.casefold() for term in ("audio", "media", "transcript"))
        return sanitize_url(value, strip_query=media_context)
    return value


def derive_episode_dir(output_root: Path, value: str, resolution: dict[str, Any]) -> Path:
    kind = str(resolution.get("kind") or "unknown")
    platform = slugify(kind.replace("local_", "local"), "source")
    title = ""
    if isinstance(resolution.get("episode"), dict):
        title = str(resolution["episode"].get("title") or "")
    title = title or str(resolution.get("title") or "")
    if not title:
        if Path(value).expanduser().exists():
            title = Path(value).stem
        else:
            parsed = urllib.parse.urlparse(value)
            if kind == "youtube":
                title = urllib.parse.parse_qs(parsed.query).get("v", [""])[0] or parsed.path.strip("/").split("/")[-1]
            elif kind == "bilibili":
                match = re.search(r"(?:BV[0-9A-Za-z]+|av\d+)", parsed.path, re.I)
                title = match.group(0) if match else "bilibili-video"
            else:
                title = Path(parsed.path).stem or parsed.netloc.split(".")[0]
    return (output_root / platform / f"{slugify(title)}-{source_key(value)}").resolve()


def run_script(name: str, arguments: list[str]) -> tuple[int, dict[str, Any], str]:
    command = [sys.executable, str(SCRIPT_DIR / name), *arguments]
    try:
        result = subprocess.run(command, text=True, capture_output=True, encoding="utf-8", errors="replace", timeout=60 * 60)
    except subprocess.TimeoutExpired:
        return 124, {"status": "blocked", "stage": name.removesuffix(".py"), "error": "helper timed out after 60 minutes"}, "helper timed out after 60 minutes"
    payload: dict[str, Any] = {}
    for stream in (result.stdout, result.stderr):
        try:
            candidate = json.loads(stream)
            if isinstance(candidate, dict):
                payload = candidate
                break
        except json.JSONDecodeError:
            continue
    diagnostic = (result.stderr or result.stdout)[-4000:]
    return result.returncode, payload, diagnostic


def choose_subtitle(paths: list[str], language_order: list[str]) -> Path | None:
    candidates = [Path(path) for path in paths if Path(path).suffix.lower() in TRANSCRIPT_EXTENSIONS]
    if not candidates:
        return None
    def score(path: Path) -> tuple[int, int, str]:
        lowered = path.name.casefold().replace("_", "-")
        language_score = next((index for index, language in enumerate(language_order) if f".{language.casefold()}" in lowered or f"-{language.casefold()}." in lowered), len(language_order))
        extension_score = {".vtt": 0, ".srt": 1, ".json": 2, ".txt": 3}.get(path.suffix.lower(), 9)
        return language_score, extension_score, path.name
    return sorted(candidates, key=score)[0]


def download_text(url: str, target: Path, max_bytes: int = 20_000_000, allow_private: bool = False) -> Path:
    request = urllib.request.Request(url, headers={"User-Agent": "podcast-reader/2.0", "Accept": "text/*,application/json,application/xml;q=0.8,*/*;q=0.1"})
    partial = target.with_suffix(target.suffix + ".part")
    try:
        with safe_urlopen(request, timeout=60, allow_private=allow_private) as response:
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type in {"text/html", "application/xhtml+xml"}:
                raise ValueError(f"transcript URL returned a webpage instead of transcript data: {content_type}")
            data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("transcript exceeds 20 MB safety limit")
        partial.write_bytes(data)
        partial.replace(target)
        return target
    except Exception:
        if partial.exists():
            partial.unlink()
        raise


def preserve_raw_transcript(source: Path, episode_dir: Path) -> Path:
    raw = episode_dir / f"transcript-raw{source.suffix.lower() or '.txt'}"
    if source.resolve() != raw.resolve():
        shutil.copy2(source, raw)
    return raw


def ensure_source_record(episode_dir: Path, source_input: str, resolution: dict[str, Any]) -> None:
    target = episode_dir / "source.json"
    if target.is_file():
        return
    kind = str(resolution.get("kind") or "")
    record = {
        "kind": resolution.get("kind"),
        "source": sanitize_url(source_input, strip_query=kind in {"media_url", "audio_url"}),
        "path": resolution.get("path"),
        "title": (resolution.get("episode") or {}).get("title") if isinstance(resolution.get("episode"), dict) else resolution.get("title"),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write_json(target, record)


def artifact_inventory(episode_dir: Path) -> dict[str, list[str]]:
    result = {"metadata": [], "transcripts": [], "indexes": [], "media": [], "analysis": [], "visual": [], "other": []}
    for path in sorted(episode_dir.rglob("*")):
        if not path.is_file() or path.name.endswith(".part"):
            continue
        relative = path.relative_to(episode_dir).as_posix()
        if path.name in {"source.json", "source-info.json", "ingest-result.json", "bundle.json"}:
            category = "metadata"
        elif path.name.startswith("transcript") or path.suffix.lower() in {".srt", ".vtt", ".ttml", ".ass"}:
            category = "transcripts"
        elif path.name == "chunks.json":
            category = "indexes"
        elif path.suffix.lower() in MEDIA_EXTENSIONS:
            category = "media"
        elif path.name in {"analysis.md", "summary.md", "evidence.json"} or path.suffix.lower() == ".csv":
            category = "analysis"
        elif relative.startswith("frames/"):
            category = "visual"
        else:
            category = "other"
        result[category].append(relative)
    return result


def normalize_and_index(source: Path, episode_dir: Path, language: str | None, method: str, warnings: list[dict[str, str]]) -> bool:
    arguments = [str(source), "--output-dir", str(episode_dir), "--method", method]
    if language:
        arguments.extend(["--language", language])
    code, _, diagnostic = run_script("normalize_transcript.py", arguments)
    if code != 0:
        warnings.append({"stage": "normalization", "message": diagnostic or "transcript normalization failed"})
        return False
    code, _, diagnostic = run_script("chunk_transcript.py", [str(episode_dir / "transcript.json"), "-o", str(episode_dir / "chunks.json")])
    if code != 0:
        warnings.append({"stage": "indexing", "message": diagnostic or "chunk indexing failed"})
        return False
    return True


def cache_satisfies(bundle: dict[str, Any], episode_dir: Path, mode: str, languages: list[str]) -> bool:
    request = bundle.get("request") if isinstance(bundle.get("request"), dict) else {}
    if request.get("mode") == mode and request.get("languages") == languages:
        return True
    if mode == "metadata":
        return (episode_dir / "source.json").is_file()
    if mode == "subtitles":
        return bundle.get("transcript_status") == "normalized"
    if mode == "auto":
        return bundle.get("status") in {"ready_for_analysis", "needs_transcription", "analyzed"}
    media = [episode_dir / path for path in (bundle.get("artifacts") or {}).get("media", [])]
    if mode == "video":
        return any(path.suffix.lower() in {".mp4", ".mkv", ".mov", ".webm"} for path in media)
    if mode == "audio":
        return any(path.suffix.lower() in {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".opus", ".flac"} for path in media)
    if mode == "all":
        return bundle.get("transcript_status") == "normalized" and any(path.suffix.lower() in {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".opus", ".flac"} for path in media)
    return False


def write_bundle(episode_dir: Path, source_input: str, resolution: dict[str, Any], status: str, transcript_status: str, warnings: list[dict[str, str]], next_actions: list[str], request: dict[str, Any] | None = None) -> dict[str, Any]:
    bundle = {
        "schema_version": "1.0",
        "bundle_id": source_key(source_input),
        "source_input": sanitize_url(source_input),
        "resolution": sanitize_for_storage(resolution),
        "status": status,
        "transcript_status": transcript_status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "episode_dir": str(episode_dir),
        "artifacts": artifact_inventory(episode_dir),
        "warnings": warnings,
        "next_actions": next_actions,
        "request": request or {},
        "provenance_note": "Raw acquired material, normalized transcript, generated analysis, and external verification must remain distinguishable.",
    }
    path = episode_dir / "bundle.json"
    atomic_write_json(path, bundle)
    bundle["artifacts"] = artifact_inventory(episode_dir)
    atomic_write_json(path, bundle)
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--output-root", default="outputs/podcast-reader")
    parser.add_argument("--output-dir", help="Use an exact episode directory instead of a derived stable directory")
    parser.add_argument("--query", help="Episode title/GUID for feed selection")
    parser.add_argument("--latest", action="store_true")
    parser.add_argument("--mode", choices=("auto", "metadata", "subtitles", "audio", "video", "all"), default="auto")
    parser.add_argument("--languages", default="zh-Hans,zh-Hant,zh-CN,zh-TW,zh,en,ja,ko")
    parser.add_argument("--transcript", help="Attach a completed transcript to this source bundle without reacquiring media")
    parser.add_argument("--transcript-method", default="generated", help="Provenance label for --transcript")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--allow-private-network", action="store_true", help="Allow explicitly trusted local/private URL targets")
    args = parser.parse_args()

    # Transcript attachment is a local resume operation. Reuse the existing
    # resolution so a temporary platform outage cannot block completed work.
    cached_resolution: dict[str, Any] | None = None
    if args.transcript and args.output_dir:
        cached_bundle_path = Path(args.output_dir).expanduser().resolve() / "bundle.json"
        if cached_bundle_path.is_file():
            cached_bundle = json.loads(cached_bundle_path.read_text(encoding="utf-8-sig"))
            if cached_bundle.get("bundle_id") == source_key(args.input) and isinstance(cached_bundle.get("resolution"), dict):
                cached_resolution = cached_bundle["resolution"]
    resolution = cached_resolution or resolve_input(args.input, args.query, no_network=False, latest=args.latest, allow_private=args.allow_private_network)
    output_root = Path(args.output_root).expanduser().resolve()
    episode_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else derive_episode_dir(output_root, args.input, resolution)
    episode_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = episode_dir / "bundle.json"
    language_order = [value.strip() for value in args.languages.split(",") if value.strip()]
    if bundle_path.exists() and not args.refresh and not args.transcript:
        existing = json.loads(bundle_path.read_text(encoding="utf-8"))
        if existing.get("bundle_id") == source_key(args.input) and cache_satisfies(existing, episode_dir, args.mode, language_order):
            existing["cache"] = "reused"
            print(json.dumps(existing, ensure_ascii=False, indent=2))
            return 0

    warnings: list[dict[str, str]] = []
    next_actions: list[str] = []
    transcript_status = "unavailable"
    status = "partial"
    kind = resolution.get("kind")
    request_record = {"mode": args.mode, "languages": language_order}

    if args.transcript:
        transcript_source = Path(args.transcript).expanduser().resolve()
        if not transcript_source.is_file():
            raise FileNotFoundError(transcript_source)
        ensure_source_record(episode_dir, args.input, resolution)
        raw = preserve_raw_transcript(transcript_source, episode_dir)
        if normalize_and_index(raw, episode_dir, None, args.transcript_method, warnings):
            status, transcript_status = "ready_for_analysis", "normalized"
            next_actions = ["analyze transcript", "answer questions using chunks.json"]
        else:
            status, transcript_status = "partial", "unavailable"
            next_actions = ["inspect transcript format and normalization warning"]
        request_record["transcript_method"] = args.transcript_method
        bundle = write_bundle(episode_dir, args.input, resolution, status, transcript_status, warnings, next_actions, request_record)
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
        return 0 if status == "ready_for_analysis" else 1

    if kind == "local_transcript":
        source = Path(resolution["path"])
        ensure_source_record(episode_dir, args.input, resolution)
        raw = preserve_raw_transcript(source, episode_dir)
        if normalize_and_index(raw, episode_dir, None, "user_provided", warnings):
            status, transcript_status = "ready_for_analysis", "normalized"
            next_actions = ["analyze transcript", "answer questions using chunks.json"]
    elif kind == "local_media":
        source_record = {"kind": kind, "path": resolution["path"], "retrieved_at": datetime.now(timezone.utc).isoformat()}
        atomic_write_json(episode_dir / "source.json", source_record)
        status, transcript_status = "needs_transcription", "unavailable"
        next_actions = [f"transcribe local media: {resolution['path']}", "attach it with --transcript after transcription"]
    elif kind in {"youtube", "bilibili"}:
        code, result, diagnostic = run_script("ingest_media.py", [args.input, "--output-dir", str(episode_dir), "--mode", args.mode, "--sub-langs", args.languages])
        for warning in result.get("warnings", []) if isinstance(result.get("warnings"), list) else []:
            if isinstance(warning, dict):
                warnings.append({"stage": str(warning.get("stage") or "ingestion"), "message": str(warning.get("message") or warning)})
        if code != 0:
            warnings.append({"stage": str(result.get("stage") or "ingestion"), "message": str(result.get("error") or diagnostic)})
        files = result.get("files") if isinstance(result.get("files"), dict) else {"subtitles": [], "media": []}
        selected = choose_subtitle(files.get("subtitles", []), language_order)
        raw_selected = preserve_raw_transcript(selected, episode_dir) if selected else None
        if raw_selected and normalize_and_index(raw_selected, episode_dir, None, "platform_captions", warnings):
            status, transcript_status = "ready_for_analysis", "normalized"
            next_actions = ["analyze transcript", "answer questions using chunks.json"]
        elif files.get("media"):
            status, transcript_status = "needs_transcription", "unavailable"
            media_list = "; ".join(str(path) for path in files["media"])
            next_actions = [f"transcribe all acquired media in order: {media_list}", "attach the combined timestamp-preserving transcript with --transcript"]
            if files.get("video"):
                next_actions.append(f"extract visual keyframes from: {files['video'][0]}")
        else:
            status = result.get("status", "partial")
            next_actions = result.get("next_actions", ["provide a transcript or authorized local media export"])
    elif kind in {"rss", "local_rss"}:
        episode = resolution.get("episode")
        if not isinstance(episode, dict):
            status = "needs_selection"
            next_actions = ["select one episode candidate by exact title or GUID"]
        else:
            ensure_source_record(episode_dir, args.input, resolution)
            if args.mode == "metadata":
                status, transcript_status = "metadata_only", "unavailable"
                next_actions = ["rerun in subtitles or auto mode when content analysis is requested"]
            transcript_urls = episode.get("transcript_urls") or resolution.get("transcript_urls") or []
            if args.mode in {"auto", "subtitles", "all"} and transcript_urls:
                parsed = urllib.parse.urlparse(transcript_urls[0])
                suffix = Path(parsed.path).suffix.lower()
                suffix = suffix if suffix in TRANSCRIPT_EXTENSIONS else ".txt"
                try:
                    raw = download_text(transcript_urls[0], episode_dir / f"transcript-raw{suffix}", allow_private=args.allow_private_network)
                    if normalize_and_index(raw, episode_dir, None, "publisher_transcript", warnings):
                        status, transcript_status = "ready_for_analysis", "normalized"
                        next_actions = ["analyze transcript", "answer questions using chunks.json"]
                except Exception as exc:
                    warnings.append({"stage": "transcript_download", "message": str(exc)})
            should_fetch_audio = args.mode in {"audio", "all"} or (args.mode == "auto" and status != "ready_for_analysis")
            if should_fetch_audio and episode.get("audio_url"):
                fetch_args = [episode["audio_url"], "--output-dir", str(episode_dir), "--name", slugify(episode.get("title") or "episode")]
                if args.allow_private_network:
                    fetch_args.append("--allow-private-network")
                code, result, diagnostic = run_script("fetch_audio.py", fetch_args)
                if code == 0:
                    if status != "ready_for_analysis":
                        status, transcript_status = "needs_transcription", "unavailable"
                        next_actions = [f"transcribe acquired media: {result.get('path')}", "attach it with --transcript after transcription"]
                else:
                    warnings.append({"stage": "audio_download", "message": str(result.get("error") or diagnostic)})
            elif args.mode == "subtitles" and status != "ready_for_analysis":
                status, next_actions = "partial", ["no public transcript was found; rerun in auto mode or provide a transcript"]
    elif kind in {"media_url", "audio_url"}:
        media_url = resolution.get("media_url") or resolution.get("audio_url") or args.input
        ensure_source_record(episode_dir, args.input, resolution)
        if args.mode in {"metadata", "subtitles"}:
            status = "metadata_only" if args.mode == "metadata" else "partial"
            next_actions = ["rerun in auto/audio mode to acquire media for transcription"]
        else:
            fetch_args = [media_url, "--output-dir", str(episode_dir)]
            if args.allow_private_network:
                fetch_args.append("--allow-private-network")
            code, result, diagnostic = run_script("fetch_audio.py", fetch_args)
            if code == 0:
                status, transcript_status = "needs_transcription", "unavailable"
                next_actions = [f"transcribe acquired media: {result.get('path')}", "attach it with --transcript after transcription"]
            else:
                warnings.append({"stage": "media_download", "message": str(result.get("error") or diagnostic)})
    elif kind == "episode_page":
        ensure_source_record(episode_dir, args.input, resolution)
        transcript_urls = resolution.get("transcript_candidates") or []
        audio_urls = resolution.get("audio_candidates") or []
        if args.mode == "metadata":
            status, transcript_status = "metadata_only", "unavailable"
            next_actions = ["rerun in subtitles or auto mode when content analysis is requested"]
        if args.mode in {"auto", "subtitles", "all"} and transcript_urls:
            parsed = urllib.parse.urlparse(transcript_urls[0])
            suffix = Path(parsed.path).suffix.lower() if Path(parsed.path).suffix.lower() in TRANSCRIPT_EXTENSIONS else ".txt"
            try:
                raw = download_text(transcript_urls[0], episode_dir / f"transcript-raw{suffix}", allow_private=args.allow_private_network)
                if normalize_and_index(raw, episode_dir, None, "publisher_transcript", warnings):
                    status, transcript_status = "ready_for_analysis", "normalized"
                    next_actions = ["analyze transcript", "answer questions using chunks.json"]
            except Exception as exc:
                warnings.append({"stage": "transcript_download", "message": str(exc)})
        should_fetch_audio = args.mode in {"audio", "all"} or (args.mode == "auto" and status != "ready_for_analysis")
        if should_fetch_audio and len(audio_urls) == 1:
            fetch_args = [audio_urls[0], "--output-dir", str(episode_dir)]
            if args.allow_private_network:
                fetch_args.append("--allow-private-network")
            code, result, diagnostic = run_script("fetch_audio.py", fetch_args)
            if code == 0:
                if status != "ready_for_analysis":
                    status, transcript_status = "needs_transcription", "unavailable"
                    next_actions = [f"transcribe acquired media: {result.get('path')}", "attach it with --transcript after transcription"]
            else:
                warnings.append({"stage": "audio_download", "message": str(result.get("error") or diagnostic)})
        elif should_fetch_audio and status != "ready_for_analysis" and len(audio_urls) > 1:
            status, next_actions = "needs_selection", ["select the media candidate that matches this episode"]
        elif args.mode == "subtitles" and status != "ready_for_analysis":
            status, next_actions = "partial", ["no public transcript was found; rerun in auto mode or provide a transcript"]
    else:
        status = "blocked" if kind in {"unknown", "unresolved"} else "partial"
        warnings.append({"stage": "resolution", "message": str(resolution.get("error") or resolution.get("warning") or f"unsupported source kind: {kind}")})
        next_actions = ["provide a public direct media URL, feed, transcript, or local file"]

    if not next_actions:
        next_actions = ["review warnings and provide a transcript or accessible media file"]
    bundle = write_bundle(episode_dir, args.input, resolution, status, transcript_status, warnings, next_actions, request_record)
    print(json.dumps(bundle, ensure_ascii=False, indent=2))
    return 0 if status not in {"blocked"} else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
