#!/usr/bin/env python3
"""Acquire public metadata, subtitles, and audio through predictable public adapters.

The default ``auto`` mode is subtitle-first: it downloads audio only when no
subtitle track was acquired. Browser cookies are never used unless the caller
explicitly supplies ``--cookies-from-browser``.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from runtime_utils import atomic_write_json, atomic_write_text, safe_urlopen, validate_public_http_url


SUBTITLE_EXTENSIONS = {".vtt", ".srt", ".ass", ".lrc", ".ttml", ".json3"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".opus", ".flac"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm"}
MEDIA_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS
YTDLP_SPEC = "yt-dlp==2026.08.19"
CONTROL_FILES = {"bundle.json", "source.json", "source-info.json", "ingest-result.json"}
BILIBILI_ID = re.compile(r"/(?:video/)?(?P<id>BV[0-9A-Za-z]+|av\d+)", re.I)
SENSITIVE_QUERY = re.compile(r"(?:token|sig(?:nature)?|auth|secret|session|jwt|key|policy|expires?|credential|hdnea)", re.I)


def command(name: str) -> str | None:
    return shutil.which(name)


def resolve_ytdlp() -> tuple[list[str] | None, str]:
    installed = command("yt-dlp")
    if installed:
        return [installed], "installed"
    uv = command("uv")
    if uv:
        return [uv, "run", "--with", YTDLP_SPEC, "yt-dlp"], "uv-ephemeral-pinned"
    return None, "missing"


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    process_env = os.environ.copy()
    process_env.setdefault("PYTHONUTF8", "1")
    process_env.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        return subprocess.run(
            args,
            cwd=cwd,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            env=process_env,
            timeout=60 * 60,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 124, "", "operation timed out after 60 minutes")


def tail(value: str, limit: int = 4000) -> str:
    lines = [
        line.strip() for line in value.splitlines()
        if line.strip() and not re.match(r"^(Installed|Resolved|Prepared|Audited)\s+\d+\s+package", line.strip(), re.I)
    ]
    return "\n".join(lines)[-limit:]


def public_page_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    query = [(key, "[REDACTED]" if SENSITIVE_QUERY.search(key) else item) for key, item in urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)]
    return urllib.parse.urlunsplit((parsed.scheme, host + port, parsed.path, urllib.parse.urlencode(query), ""))


def classify_files(output_dir: Path) -> dict[str, list[str]]:
    result = {"subtitles": [], "audio": [], "video": [], "media": [], "other": []}
    for path in sorted(output_dir.iterdir()):
        if not path.is_file() or path.name in CONTROL_FILES or path.name.endswith(".part"):
            continue
        resolved = str(path.resolve())
        if path.suffix.lower() in SUBTITLE_EXTENSIONS:
            result["subtitles"].append(resolved)
        elif path.suffix.lower() in MEDIA_EXTENSIONS:
            result["media"].append(resolved)
            result["audio" if path.suffix.lower() in AUDIO_EXTENSIONS else "video"].append(resolved)
        else:
            result["other"].append(resolved)
    return result


def compact_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Retain useful metadata without persisting temporary signed media URLs."""
    subtitles = metadata.get("subtitles") or {}
    automatic = metadata.get("automatic_captions") or {}
    chapters = metadata.get("chapters") or []
    return {
        "id": metadata.get("id"),
        "title": metadata.get("title"),
        "description": metadata.get("description"),
        "extractor": metadata.get("extractor_key") or metadata.get("extractor"),
        "uploader": metadata.get("uploader") or metadata.get("channel"),
        "uploader_id": metadata.get("uploader_id") or metadata.get("channel_id"),
        "upload_date": metadata.get("upload_date"),
        "timestamp": metadata.get("timestamp"),
        "duration_seconds": metadata.get("duration"),
        "language": metadata.get("language"),
        "webpage_url": public_page_url(metadata.get("webpage_url") or metadata.get("original_url")) if (metadata.get("webpage_url") or metadata.get("original_url")) else None,
        "thumbnail": metadata.get("thumbnail"),
        "view_count": metadata.get("view_count"),
        "like_count": metadata.get("like_count"),
        "categories": metadata.get("categories") or [],
        "tags": metadata.get("tags") or [],
        "chapters": [
            {"start_time": item.get("start_time"), "end_time": item.get("end_time"), "title": item.get("title")}
            for item in chapters if isinstance(item, dict)
        ],
        "available_subtitles": sorted(str(key) for key in subtitles),
        "available_automatic_captions": sorted(str(key) for key in automatic),
    }


def _requested_subtitle_languages(value: str) -> list[str]:
    """Return concrete language preferences, excluding yt-dlp selectors."""
    return [
        item.strip() for item in value.split(",")
        if item.strip() and item.strip().lower() != "all" and not item.strip().startswith("-")
    ]


def _language_match_score(available: str, requested: str) -> tuple[int, str]:
    """Rank exact, script-compatible, then base-language subtitle matches."""
    left = available.casefold().replace("_", "-")
    right = requested.casefold().replace("_", "-")
    if left == right:
        return (0, left)
    simplified = {"zh-cn", "zh-hans", "zh-sg"}
    traditional = {"zh-tw", "zh-hant", "zh-hk", "zh-mo"}
    if left in simplified and right in simplified:
        return (1, left)
    if left in traditional and right in traditional:
        return (1, left)
    if left.split("-", 1)[0] == right.split("-", 1)[0]:
        return (2, left)
    return (99, left)


def subtitle_download_candidates(metadata: dict[str, Any], requested_spec: str) -> list[tuple[str, str]]:
    """Build bounded, reliable subtitle fallbacks.

    Publisher-provided tracks are preferred over automatic captions. The first
    requested language is attempted first, followed immediately by the source
    language so a throttled translation track cannot hide a usable original.
    """
    requested = _requested_subtitle_languages(requested_spec)
    source_language = str(metadata.get("language") or "").strip()
    target_order: list[str] = []
    if requested:
        target_order.append(requested[0])
    if source_language and source_language.casefold() not in {item.casefold() for item in target_order}:
        target_order.append(source_language)
    target_order.extend(
        item for item in requested
        if item.casefold() not in {existing.casefold() for existing in target_order}
    )

    human = [str(item) for item in (metadata.get("subtitles") or {}) if str(item).lower() != "live_chat"]
    automatic = [str(item) for item in (metadata.get("automatic_captions") or {}) if str(item).lower() != "live_chat"]
    result: list[tuple[str, str]] = []
    used: set[tuple[str, str]] = set()

    def add_best(kind: str, available: list[str], targets: list[str]) -> None:
        for target in targets:
            ranked = sorted((_language_match_score(item, target), item) for item in available)
            if not ranked or ranked[0][0][0] >= 99:
                continue
            candidate = (ranked[0][1], kind)
            marker = (candidate[0].casefold(), kind)
            if marker not in used:
                result.append(candidate)
                used.add(marker)

    add_best("human", human, target_order)
    auto_targets = ([source_language] if source_language else []) + target_order
    add_best("automatic", automatic, auto_targets)
    return result[:16]


def fetch_json(url: str, referer: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 podcast-reader/2.0", "Referer": referer, "Accept": "application/json"})
    with safe_urlopen(request, timeout=25) as response:
        return json.load(response)


def bilibili_public_metadata(url: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Use Bilibili's public web API as a metadata/subtitle fallback."""
    match = BILIBILI_ID.search(urllib.parse.urlparse(url).path)
    if not match:
        raise ValueError("Bilibili BV/av identifier is not present in URL")
    identifier = match.group("id")
    parameter = f"bvid={identifier}" if identifier.upper().startswith("BV") else f"aid={identifier[2:]}"
    view = fetch_json(f"https://api.bilibili.com/x/web-interface/view?{parameter}", url)
    if view.get("code") != 0 or not isinstance(view.get("data"), dict):
        raise ValueError(str(view.get("message") or "Bilibili public metadata unavailable"))
    data = view["data"]
    owner = data.get("owner") or {}
    stat = data.get("stat") or {}
    pubdate = data.get("pubdate")
    upload_date = datetime.fromtimestamp(pubdate, timezone.utc).strftime("%Y%m%d") if isinstance(pubdate, (int, float)) else None
    metadata = {
        "id": data.get("bvid") or str(data.get("aid") or identifier),
        "title": data.get("title"),
        "description": data.get("desc"),
        "extractor_key": "BiliBiliPublicMetadata",
        "uploader": owner.get("name"),
        "uploader_id": owner.get("mid"),
        "upload_date": upload_date,
        "timestamp": pubdate,
        "duration": data.get("duration"),
        "language": None,
        "webpage_url": f"https://www.bilibili.com/video/{data.get('bvid') or identifier}",
        "thumbnail": data.get("pic"),
        "view_count": stat.get("view"),
        "like_count": stat.get("like"),
        "categories": [data.get("tname")] if data.get("tname") else [],
        "tags": [],
        "chapters": [],
        "subtitles": {},
        "automatic_captions": {},
        "_bilibili": {
            "parameter": parameter,
            "pages": [
                {
                    "page": item.get("page"),
                    "cid": item.get("cid"),
                    "part": item.get("part"),
                    "duration": item.get("duration"),
                }
                for item in data.get("pages", [])
                if isinstance(item, dict) and item.get("cid")
            ],
        },
    }
    tracks: list[dict[str, Any]] = []
    cid = data.get("cid") or next((page.get("cid") for page in data.get("pages", []) if isinstance(page, dict) and page.get("cid")), None)
    if cid:
        player = fetch_json(f"https://api.bilibili.com/x/player/v2?{parameter}&cid={cid}", metadata["webpage_url"])
        subtitle_data = (player.get("data") or {}).get("subtitle") or {}
        tracks = [item for item in subtitle_data.get("subtitles", []) if isinstance(item, dict) and item.get("subtitle_url")]
        metadata["subtitles"] = {str(item.get("lan") or "unknown"): [{"name": item.get("lan_doc")}] for item in tracks}
    return metadata, tracks


def redact_remote_urls(value: str) -> str:
    """Prevent temporary signed CDN URLs from entering durable diagnostics."""
    return re.sub(r"https?://[^\s'\"]+", "[REMOTE_URL_REDACTED]", value)


CONTENT_RANGE = re.compile(r"bytes\s+(\d+)-(\d+)/(\d+|\*)", re.I)


def download_public_stream(
    url: str,
    destination: Path,
    referer: str,
    *,
    chunk_size: int = 8 * 1024 * 1024,
    max_bytes: int = 2 * 1024 * 1024 * 1024,
    max_stalls: int = 5,
) -> dict[str, int | None]:
    """Download a public CDN object with byte-range resume and size checks."""
    if chunk_size <= 0 or max_bytes <= 0 or max_stalls < 1:
        raise ValueError("download bounds must be positive")
    destination.parent.mkdir(parents=True, exist_ok=True)
    offset = 0
    expected_size: int | None = None
    stalls = 0
    headers = {
        "Referer": referer,
        "User-Agent": "Mozilla/5.0 podcast-reader/2.0",
        "Accept": "*/*",
    }
    with destination.open("wb") as stream:
        while expected_size is None or offset < expected_size:
            requested_end = offset + chunk_size - 1
            if expected_size is not None:
                requested_end = min(requested_end, expected_size - 1)
            request = urllib.request.Request(url, headers={**headers, "Range": f"bytes={offset}-{requested_end}"})
            before = offset
            try:
                with safe_urlopen(request, timeout=90) as response:
                    status = int(getattr(response, "status", response.getcode()))
                    content_range = response.headers.get("Content-Range") or ""
                    match = CONTENT_RANGE.fullmatch(content_range.strip())
                    if status == 206:
                        if not match:
                            raise RuntimeError("range response omitted a valid Content-Range header")
                        response_start = int(match.group(1))
                        if response_start != offset:
                            raise RuntimeError(f"range response started at {response_start}, expected {offset}")
                        if match.group(3) != "*":
                            total = int(match.group(3))
                            if expected_size is not None and total != expected_size:
                                raise RuntimeError("remote object size changed during download")
                            expected_size = total
                    elif status == 200:
                        if offset:
                            raise RuntimeError("server stopped honoring byte-range resume")
                        length = response.headers.get("Content-Length")
                        expected_size = int(length) if length and length.isdigit() else None
                    else:
                        raise RuntimeError(f"unexpected HTTP status {status}")
                    if expected_size is not None and expected_size > max_bytes:
                        raise RuntimeError(f"remote media exceeds {max_bytes} byte safety limit")

                    while True:
                        payload = response.read(min(1024 * 1024, max_bytes - offset + 1))
                        if not payload:
                            break
                        stream.write(payload)
                        offset += len(payload)
                        if offset > max_bytes or (expected_size is not None and offset > expected_size):
                            raise RuntimeError("remote media exceeded its declared or configured size")
                    stream.flush()
                    os.fsync(stream.fileno())
            except Exception:
                if offset == before:
                    stalls += 1
                    if stalls >= max_stalls:
                        raise
                else:
                    stalls = 0
                continue
            if offset == before:
                stalls += 1
                if stalls >= max_stalls:
                    raise RuntimeError("remote media download made no progress")
            else:
                stalls = 0
            if expected_size is None:
                break
    if expected_size is not None and offset != expected_size:
        raise RuntimeError(f"remote media is incomplete: {offset}/{expected_size} bytes")
    return {"size_bytes": offset, "expected_size_bytes": expected_size}


def media_duration(path: Path, cwd: Path) -> float:
    probe = run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        cwd,
    )
    if probe.returncode != 0:
        raise RuntimeError(tail(probe.stderr or probe.stdout) or "ffprobe could not read media duration")
    try:
        duration = float(probe.stdout.strip())
    except ValueError as exc:
        raise RuntimeError("ffprobe returned an invalid media duration") from exc
    if duration <= 0:
        raise RuntimeError("media duration is not positive")
    return duration


def duration_is_complete(actual: float, expected: float | int | None) -> bool:
    if not isinstance(expected, (int, float)) or expected <= 0:
        return actual > 0
    tolerance = max(3.0, float(expected) * 0.005)
    return abs(actual - float(expected)) <= tolerance


def write_bilibili_audio(
    metadata: dict[str, Any],
    output_dir: Path,
    source_url: str,
    audio_format: str,
    force: bool,
) -> tuple[list[str], list[dict[str, str]]]:
    """Acquire each public Bilibili part through the web play API and normalize it."""
    context = metadata.get("_bilibili") or {}
    parameter = context.get("parameter")
    pages = context.get("pages") or []
    if not parameter or not pages:
        return [], [{"stage": "audio", "message": "Bilibili public audio fallback has no page identifiers"}]

    codec_args = {
        "mp3": ["-c:a", "libmp3lame", "-q:a", "2"],
        "m4a": ["-c:a", "aac", "-b:a", "128k"],
        "opus": ["-c:a", "libopus", "-b:a", "96k"],
        "wav": ["-c:a", "pcm_s16le"],
    }
    written: list[str] = []
    warnings: list[dict[str, str]] = []
    video_id = re.sub(r"[^A-Za-z0-9_-]+", "-", str(metadata.get("id") or "bilibili"))
    referer = metadata.get("webpage_url") or source_url

    for ordinal, page in enumerate(pages, start=1):
        page_number = int(page.get("page") or ordinal)
        cid = page.get("cid")
        expected_duration = page.get("duration")
        target = output_dir / f"bilibili-{video_id}-p{page_number:02d}.{audio_format}"
        existing_audio = sorted({
            path for path in output_dir.glob(f"bilibili-{video_id}-p{page_number:02d}.*")
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
        })
        if not force:
            reused = False
            for candidate in existing_audio:
                try:
                    cached_duration = media_duration(candidate, output_dir)
                    if duration_is_complete(cached_duration, expected_duration):
                        written.append(str(candidate.resolve()))
                        reused = True
                        break
                    warnings.append({
                        "stage": "audio",
                        "message": f"discarded incomplete cached Bilibili audio for part {page_number}: "
                        f"{cached_duration:.3f}s acquired vs {float(expected_duration):.3f}s expected",
                    })
                except Exception as exc:
                    warnings.append({"stage": "audio", "message": f"discarded unreadable cached Bilibili audio for part {page_number}: {exc}"})
                candidate.unlink(missing_ok=True)
            if reused:
                continue
        try:
            play = fetch_json(
                f"https://api.bilibili.com/x/player/playurl?{parameter}&cid={cid}&qn=16&fnval=16&fourk=0",
                referer,
            )
            if play.get("code") != 0 or not isinstance(play.get("data"), dict):
                raise ValueError(str(play.get("message") or "public play API unavailable"))
            data = play["data"]
            audio_candidates = ((data.get("dash") or {}).get("audio") or [])
            selected = max(
                (item for item in audio_candidates if isinstance(item, dict)),
                key=lambda item: int(item.get("bandwidth") or item.get("id") or 0),
                default=None,
            )
            media_url = (selected or {}).get("baseUrl") or (selected or {}).get("base_url")
            if not media_url:
                progressive = next((item for item in data.get("durl", []) if isinstance(item, dict) and item.get("url")), None)
                media_url = (progressive or {}).get("url")
            if not media_url:
                raise ValueError("public play API returned no usable media stream")

            with tempfile.NamedTemporaryFile(prefix=f".{target.stem}.", suffix=".source.m4a", dir=output_dir, delete=False) as handle:
                source_temporary = Path(handle.name)
            with tempfile.NamedTemporaryFile(prefix=f".{target.stem}.", suffix=target.suffix, dir=output_dir, delete=False) as handle:
                converted_temporary = Path(handle.name)
            try:
                download_public_stream(str(media_url), source_temporary, referer)
                source_duration = media_duration(source_temporary, output_dir)
                if not duration_is_complete(source_duration, expected_duration):
                    raise RuntimeError(
                        f"Bilibili source stream is incomplete: {source_duration:.3f}s acquired "
                        f"vs {float(expected_duration):.3f}s expected"
                    )
                if audio_format == "m4a":
                    os.replace(source_temporary, target)
                else:
                    conversion = run(
                        [
                            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                            "-i", str(source_temporary), "-vn",
                            *codec_args[audio_format], str(converted_temporary),
                        ],
                        output_dir,
                    )
                    if conversion.returncode != 0 or not converted_temporary.is_file() or converted_temporary.stat().st_size == 0:
                        detail = redact_remote_urls(tail(conversion.stderr or conversion.stdout))
                        raise RuntimeError(detail or "ffmpeg did not produce an audio file")
                    converted_duration = media_duration(converted_temporary, output_dir)
                    if not duration_is_complete(converted_duration, expected_duration):
                        raise RuntimeError(
                            f"normalized Bilibili audio is incomplete: {converted_duration:.3f}s acquired "
                            f"vs {float(expected_duration):.3f}s expected"
                        )
                    os.replace(converted_temporary, target)
                for obsolete in existing_audio:
                    if obsolete != target:
                        obsolete.unlink(missing_ok=True)
            finally:
                source_temporary.unlink(missing_ok=True)
                converted_temporary.unlink(missing_ok=True)
            written.append(str(target.resolve()))
        except Exception as exc:
            warnings.append({
                "stage": "audio",
                "message": f"Bilibili public audio fallback failed for part {page_number}: {redact_remote_urls(str(exc))}",
            })
    return written, warnings


def write_bilibili_subtitles(tracks: list[dict[str, Any]], output_dir: Path, source_url: str, video_id: str) -> list[str]:
    written = []
    for track in tracks:
        subtitle_url = str(track["subtitle_url"])
        if subtitle_url.startswith("//"):
            subtitle_url = "https:" + subtitle_url
        payload = fetch_json(subtitle_url, source_url)
        body = payload.get("body") or []
        lines = ["WEBVTT", ""]
        for item in body:
            if not isinstance(item, dict) or not str(item.get("content") or "").strip():
                continue
            def stamp(value: Any) -> str:
                seconds = float(value or 0)
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                remainder = seconds % 60
                return f"{hours:02d}:{minutes:02d}:{remainder:06.3f}"
            lines.extend([f"{stamp(item.get('from'))} --> {stamp(item.get('to'))}", str(item["content"]).strip(), ""])
        if len(lines) > 2:
            language = re.sub(r"[^A-Za-z0-9_-]+", "-", str(track.get("lan") or "unknown"))
            target = output_dir / f"bilibili-{video_id}.{language}.vtt"
            atomic_write_text(target, "\n".join(lines))
            written.append(str(target.resolve()))
    return written


def common_args(cookies_from_browser: str | None) -> list[str]:
    args = ["--ignore-config", "--no-playlist", "--no-warnings"]
    if cookies_from_browser:
        args.extend(["--cookies-from-browser", cookies_from_browser])
    return args


def write_result(output_dir: Path, result: dict[str, Any]) -> None:
    atomic_write_json(output_dir / "ingest-result.json", result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Public media URL or existing local media file")
    parser.add_argument("--output-dir", default="outputs/podcast-reader/media")
    parser.add_argument("--mode", choices=("auto", "metadata", "subtitles", "audio", "video", "all"), default="auto")
    parser.add_argument("--sub-langs", default="zh-Hans,zh-Hant,zh-CN,zh-TW,zh,en,ja,ko,all,-live_chat")
    parser.add_argument("--audio-format", choices=("mp3", "m4a", "opus", "wav"), default="m4a")
    parser.add_argument("--max-duration-minutes", type=float, default=480.0, help="Refuse automatic audio extraction beyond this duration; 0 disables")
    parser.add_argument("--force", action="store_true", help="Allow yt-dlp to overwrite existing acquired files")
    parser.add_argument("--cookies-from-browser", help="Explicit authorized yt-dlp browser cookie source; never set automatically")
    args = parser.parse_args()
    validate_public_http_url(args.input)

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    local = Path(args.input).expanduser()
    if local.exists():
        source = {
            "kind": "local_media",
            "source": args.input,
            "path": str(local.resolve()),
            "size_bytes": local.stat().st_size,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }
        atomic_write_json(output_dir / "source.json", source)
        local_path = str(local.resolve())
        local_video = [local_path] if local.suffix.lower() in VIDEO_EXTENSIONS else []
        local_audio = [local_path] if local.suffix.lower() in AUDIO_EXTENSIONS else []
        result = {"status": "ready", "source": source, "files": {"subtitles": [], "audio": local_audio, "video": local_video, "media": [local_path], "other": []}, "warnings": [], "next_actions": ["transcribe local media"]}
        write_result(output_dir, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    yt_dlp, adapter = resolve_ytdlp()
    if not yt_dlp:
        result = {
            "status": "blocked",
            "stage": "dependency",
            "error": "yt-dlp is unavailable and uv cannot provide it ephemerally",
            "install": ["uv tool install yt-dlp", "python -m pip install -U yt-dlp"],
        }
        write_result(output_dir, result)
        print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    base = yt_dlp + common_args(args.cookies_from_browser)
    metadata_run = run(base + ["--dump-single-json", "--skip-download", args.input], output_dir)
    public_subtitle_tracks: list[dict[str, Any]] = []
    metadata_warning: dict[str, str] | None = None
    if metadata_run.returncode == 0:
        try:
            raw_metadata = json.loads(metadata_run.stdout)
        except json.JSONDecodeError:
            raw_metadata = {}
    else:
        raw_metadata = {}
    if not raw_metadata:
        try:
            raw_metadata, public_subtitle_tracks = bilibili_public_metadata(args.input)
            adapter = "bilibili-public-api"
            metadata_warning = {"stage": "metadata", "message": f"yt-dlp metadata failed; public metadata fallback used: {tail(metadata_run.stderr or metadata_run.stdout)}"}
        except Exception as fallback_error:
            result = {"status": "blocked", "stage": "metadata", "source": public_page_url(args.input), "error": tail(metadata_run.stderr or metadata_run.stdout) or "yt-dlp returned invalid metadata JSON", "fallback_error": str(fallback_error)}
            write_result(output_dir, result)
            print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
            return 1

    info = compact_metadata(raw_metadata)
    source = {
        "kind": "remote_media",
        "source_url": public_page_url(args.input),
        "canonical_url": info.get("webpage_url") or public_page_url(args.input),
        "platform": info.get("extractor"),
        "id": info.get("id"),
        "title": info.get("title"),
        "show_or_uploader": info.get("uploader"),
        "published": info.get("upload_date"),
        "duration_seconds": info.get("duration_seconds"),
        "language": info.get("language"),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "ingestion_adapter": f"yt-dlp:{adapter}",
        "cookie_mode": "explicit" if args.cookies_from_browser else "none",
    }
    atomic_write_json(output_dir / "source.json", source)
    atomic_write_json(output_dir / "source-info.json", info)

    warnings: list[dict[str, str]] = [metadata_warning] if metadata_warning else []
    template = "%(title).180B [%(id)s].%(ext)s"
    overwrite = ["--force-overwrites"] if args.force else ["--no-overwrites"]

    using_bilibili_public_api = adapter == "bilibili-public-api"
    if args.mode in {"auto", "subtitles", "all"}:
        if public_subtitle_tracks:
            try:
                write_bilibili_subtitles(public_subtitle_tracks, output_dir, args.input, str(raw_metadata.get("id") or "video"))
            except Exception as exc:
                warnings.append({"stage": "subtitles", "message": f"Bilibili public subtitle fallback failed: {exc}"})
        elif using_bilibili_public_api:
            warnings.append({"stage": "subtitles", "message": "publisher exposes no public subtitle tracks"})
        else:
            candidates = subtitle_download_candidates(raw_metadata, args.sub_langs)
            subtitle_failures: list[str] = []
            if not classify_files(output_dir)["subtitles"]:
                for language, track_kind in candidates:
                    write_flag = "--write-subs" if track_kind == "human" else "--write-auto-subs"
                    subtitle_cmd = base + overwrite + [
                        "--skip-download", write_flag, "--sub-langs", language,
                        "--sub-format", "vtt/srt/best", "--restrict-filenames",
                        "-o", template, args.input,
                    ]
                    subtitle_run = run(subtitle_cmd, output_dir)
                    if classify_files(output_dir)["subtitles"]:
                        if subtitle_failures:
                            warnings.append({
                                "stage": "subtitles",
                                "message": f"subtitle fallback succeeded with {track_kind} track {language}; "
                                f"earlier attempts failed: {' | '.join(subtitle_failures)}",
                            })
                        break
                    failure = tail(subtitle_run.stderr or subtitle_run.stdout) or "no subtitle file produced"
                    subtitle_failures.append(f"{track_kind}:{language}: {failure}")
            if not classify_files(output_dir)["subtitles"]:
                if not candidates:
                    subtitle_failures.append("metadata advertised no matching subtitle tracks")
                warnings.append({"stage": "subtitles", "message": " | ".join(subtitle_failures)})

    files = classify_files(output_dir)
    want_audio = args.mode in {"audio", "all"} or (args.mode == "auto" and not files["subtitles"])
    duration = source.get("duration_seconds")
    if want_audio and args.max_duration_minutes and isinstance(duration, (int, float)) and duration > args.max_duration_minutes * 60:
        warnings.append({"stage": "audio", "message": f"duration {duration:.0f}s exceeds automatic limit; rerun with --max-duration-minutes 0 after confirming scope"})
        want_audio = False
    if want_audio and not command("ffmpeg"):
        warnings.append({"stage": "dependency", "message": "ffmpeg is required for audio extraction"})
        want_audio = False
    if want_audio:
        if using_bilibili_public_api:
            _, fallback_warnings = write_bilibili_audio(
                raw_metadata, output_dir, args.input, args.audio_format, args.force
            )
            warnings.extend(fallback_warnings)
        else:
            audio_cmd = base + overwrite + [
                "-x", "--audio-format", args.audio_format, "--audio-quality", "0",
                "--restrict-filenames", "-o", template, args.input,
            ]
            audio_run = run(audio_cmd, output_dir)
            if audio_run.returncode != 0:
                warnings.append({"stage": "audio", "message": tail(audio_run.stderr or audio_run.stdout)})

    want_video = args.mode == "video"
    if want_video and args.max_duration_minutes and isinstance(duration, (int, float)) and duration > args.max_duration_minutes * 60:
        warnings.append({"stage": "video", "message": f"duration {duration:.0f}s exceeds automatic limit; rerun with --max-duration-minutes 0 after confirming scope"})
        want_video = False
    if want_video and not command("ffmpeg"):
        warnings.append({"stage": "dependency", "message": "ffmpeg is required to merge bounded video and audio streams"})
        want_video = False
    if want_video:
        video_cmd = base + overwrite + [
            "-f", "bv*[height<=720]+ba/b[height<=720]",
            "--merge-output-format", "mp4", "--restrict-filenames",
            "-o", template, args.input,
        ]
        video_run = run(video_cmd, output_dir)
        if video_run.returncode != 0:
            warnings.append({"stage": "video", "message": tail(video_run.stderr or video_run.stdout)})

    files = classify_files(output_dir)
    if files["subtitles"]:
        transcript_status = "captions_acquired"
        next_actions = ["normalize the best subtitle track", "build retrieval index"]
    elif files["media"]:
        transcript_status = "needs_transcription"
        next_actions = ["transcribe acquired media with diarization when needed", "normalize transcript", "build retrieval index"]
        if files["video"]:
            next_actions.append("extract keyframes only when visual evidence affects the answer")
    else:
        transcript_status = "unavailable"
        next_actions = ["provide a public transcript or authorized local media export"]
    status = "ready" if files["subtitles"] or files["media"] else "partial"
    if args.mode == "metadata":
        status, next_actions = "metadata_only", ["acquire captions or audio when content analysis is requested"]
    result = {
        "status": status,
        "transcript_status": transcript_status,
        "source": source,
        "files": files,
        "warnings": warnings,
        "next_actions": next_actions,
    }
    write_result(output_dir, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
