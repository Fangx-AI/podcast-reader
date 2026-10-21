#!/usr/bin/env python3
"""Explicit anonymous Bilibili audio adapter for an already installed bili-cli.

This helper never installs packages or reads cookies. It writes the same
ingest-result contract as ingest_media.py, without changing the default route.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
from datetime import datetime, timezone
import importlib
import io
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any
from urllib.parse import parse_qs, urlsplit

from ingest_media import command, download_public_stream, duration_is_complete, media_duration, redact_remote_urls, run
from runtime_utils import atomic_write_json, sha256_file


BVID = re.compile(r"BV[0-9A-Za-z]{10}")
MAX_BYTES = 2 * 1024 * 1024 * 1024


def parse_source(value: str, page: int | None = None) -> tuple[str, int | None]:
    """Accept only a BV ID or canonical Bilibili video URL, preserving p=."""
    value = value.strip()
    if BVID.fullmatch(value):
        bvid, url_page = value, None
    else:
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"}
                or parsed.hostname not in {"bilibili.com", "www.bilibili.com", "m.bilibili.com"}
                or parsed.username or parsed.password or parsed.port not in {None, 80, 443}):
            raise ValueError("Use a BV ID or a public bilibili.com/video/BV... URL without credentials")
        match = re.fullmatch(r"/video/(BV[0-9A-Za-z]{10})/?", parsed.path)
        if not match:
            raise ValueError("Use the canonical BV video URL; short links and av IDs are not supported here")
        bvid = match.group(1)
        values = parse_qs(parsed.query, keep_blank_values=True).get("p", [])
        if len(values) > 1 or (values and not values[0].isdigit()):
            raise ValueError("The URL must contain at most one positive integer p selection")
        url_page = int(values[0]) if values else None
    if page is not None and (type(page) is not int or page < 1):
        raise ValueError("--page must be a positive integer")
    if url_page is not None and url_page < 1:
        raise ValueError("URL p must be a positive integer")
    if page is not None and url_page is not None and page != url_page:
        raise ValueError("--page conflicts with the URL p selection")
    return bvid, page if page is not None else url_page


def positive_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) and value > 0 else None


def published_date(value: Any) -> str | None:
    """Match the existing ingestion date format without trusting raw timestamps."""
    timestamp = positive_number(value)
    if timestamp is None:
        return None
    try:
        return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y%m%d")
    except (OverflowError, OSError, ValueError):
        return None


def page_records(info: dict[str, Any]) -> list[dict[str, Any]]:
    pages = info.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError("Public metadata contains no selectable video parts")
    result = []
    seen = set()
    for item in pages:
        if (not isinstance(item, dict) or type(item.get("page")) is not int
                or item["page"] < 1 or item["page"] in seen
                or type(item.get("cid")) is not int or item["cid"] < 1):
            raise ValueError("Public metadata contains invalid or duplicate part identifiers")
        seen.add(item["page"])
        duration = positive_number(item.get("duration"))
        if duration is None and len(pages) == 1:
            duration = positive_number(info.get("duration"))
        result.append({"page": item["page"], "cid": item["cid"],
                       "part": str(item.get("part") or ""), "duration": duration})
    return sorted(result, key=lambda item: item["page"])


async def selected_audio_url(client: Any, bvid: str, selected: dict[str, Any], *, timeout: float) -> str:
    if selected["page"] == 1:
        return await asyncio.wait_for(client.get_audio_url(bvid, credential=None), timeout)
    # bili-cli 0.6.2 hard-codes page_index=0. Use its installed SDK for other
    # explicitly selected parts instead of silently acquiring the first part.
    video = importlib.import_module("bilibili_api.video")
    instance = video.Video(bvid=bvid, credential=None)
    data = await asyncio.wait_for(instance.get_download_url(cid=selected["cid"]), timeout)
    detector = video.VideoDownloadURLDataDetecter(data)
    streams = detector.detect_best_streams(audio_max_quality=video.AudioQuality._64K,
                                          no_dolby_audio=True, no_hires=True)
    if detector.check_flv_mp4_stream():
        candidate = streams[0] if streams else None
    else:
        candidate = next((item for item in streams if item is not None and hasattr(item, "audio_quality")), None)
    if candidate is None or not getattr(candidate, "url", None):
        raise RuntimeError("The selected part has no anonymous public audio stream")
    return candidate.url


async def acquire(value: str, output_dir: Path, *, page: int | None = None, mode: str = "audio",
                  max_duration_minutes: float = 480, max_bytes: int = MAX_BYTES,
                  timeout: float = 60, force: bool = False, client: Any = None) -> dict[str, Any]:
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "status": "blocked", "transcript_status": "unavailable", "source": {},
        "files": {"subtitles": [], "audio": [], "video": [], "media": [], "other": []},
        "warnings": [], "next_actions": [],
    }
    stage = "input"
    temporary: list[Path] = []
    try:
        if (mode not in {"metadata", "audio"} or not math.isfinite(max_duration_minutes)
                or max_duration_minutes < 0 or type(max_bytes) is not int or max_bytes < 1
                or not math.isfinite(timeout) or timeout <= 0):
            raise ValueError("Require metadata/audio mode, finite nonnegative duration limit, and positive size/timeout limits")
        bvid, requested_page = parse_source(value, page)
        stage = "dependency"
        if client is None:
            try:
                client = importlib.import_module("bili_cli.client")
            except ImportError as exc:
                raise RuntimeError("bili_cli is unavailable; use the Python environment where bilibili-cli is already installed. Nothing was installed") from exc
        stage = "metadata"
        # Third-party diagnostics can contain temporary stream URLs. Do not
        # copy their stdout/stderr into the result or terminal JSON stream.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            info = await asyncio.wait_for(client.get_video_info(bvid, credential=None), timeout)
        if not isinstance(info, dict) or (info.get("bvid") and info["bvid"] != bvid):
            raise ValueError("Public metadata does not match the requested video")
        pages = page_records(info)
        selected = next((item for item in pages if item["page"] == requested_page), None) if requested_page else (pages[0] if len(pages) == 1 else None)
        if requested_page and selected is None:
            raise ValueError("The requested part does not exist in public metadata")
        canonical = f"https://www.bilibili.com/video/{bvid}/"
        if selected and (len(pages) > 1 or requested_page is not None):
            canonical += f"?p={selected['page']}"
        owner = info.get("owner") if isinstance(info.get("owner"), dict) else {}
        source = {
            "kind": "remote_media", "source_url": canonical, "canonical_url": canonical,
            "platform": "Bilibili", "id": bvid,
            "title": info.get("title"), "show_or_uploader": owner.get("name"),
            "published": published_date(info.get("pubdate")),
            "duration_seconds": selected["duration"] if selected else positive_number(info.get("duration")),
            "language": None, "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "ingestion_adapter": "bili-cli:anonymous", "cookie_mode": "none",
            "selected_part": selected, "part_count": len(pages),
        }
        result["source"], result["available_parts"] = source, pages
        atomic_write_json(output_dir / "source.json", source)
        atomic_write_json(output_dir / "source-info.json", {
            "id": bvid, "title": info.get("title"), "description": info.get("desc"),
            "uploader": owner.get("name"), "timestamp": info.get("pubdate"),
            "duration_seconds": source["duration_seconds"], "webpage_url": canonical,
            "pages": pages, "selected_part": selected, "extractor": "BiliCliAnonymous",
        })
        if selected is None:
            result["status"] = "needs_selection"
            result["next_actions"] = ["Select exactly one part with --page N or a canonical URL containing ?p=N; use a separate output directory for each part"]
        elif mode == "metadata":
            result["status"] = "metadata_only"
            result["next_actions"] = ["Run this adapter explicitly with --mode audio to acquire the selected part"]
        else:
            stage = "duration"
            expected = selected["duration"]
            if expected is None:
                raise ValueError("Selected part has no known positive duration; cannot enforce scope or verify complete media")
            if max_duration_minutes and expected > max_duration_minutes * 60:
                raise ValueError("Selected part exceeds --max-duration-minutes; increase it or explicitly use 0 after confirming scope")
            stage = "dependency"
            if not command("ffprobe") or not command("ffmpeg"):
                raise RuntimeError("ffprobe and ffmpeg are required to verify duration and retain only the audio track")
            stage = "audio"
            target = output_dir / f"bilibili-{bvid}-p{selected['page']:02d}-c{selected['cid']}.m4a"
            reuse = False
            if target.is_file() and not force:
                try:
                    reuse = (0 < target.stat().st_size <= max_bytes
                             and duration_is_complete(media_duration(target, output_dir), expected))
                except Exception:
                    pass
            if not reuse:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    stream_url = await selected_audio_url(client, bvid, selected, timeout=timeout)
                for suffix in (".download.part", ".m4a"):
                    with tempfile.NamedTemporaryFile(prefix=".bili-cli-", suffix=suffix, dir=output_dir, delete=False) as handle:
                        temporary.append(Path(handle.name))
                downloaded, audio = temporary
                download_public_stream(stream_url, downloaded, canonical, max_bytes=max_bytes)
                if not duration_is_complete(media_duration(downloaded, output_dir), expected):
                    raise RuntimeError("Downloaded media duration does not match the selected part")
                conversion = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(downloaded),
                                  "-map", "0:a:0", "-vn", "-c:a", "copy", str(audio)], output_dir)
                if (conversion.returncode or not 0 < audio.stat().st_size <= max_bytes
                        or not duration_is_complete(media_duration(audio, output_dir), expected)):
                    raise RuntimeError("Audio extraction or complete-duration verification failed")
                os.replace(audio, target)
            result.update({"status": "ready", "transcript_status": "needs_transcription",
                           "cache": "reused" if reuse else "acquired",
                           "audio_integrity": {"size_bytes": target.stat().st_size, "sha256": sha256_file(target)}})
            result["files"]["audio"] = result["files"]["media"] = [str(target)]
            result["next_actions"] = ["Transcribe this selected part, then attach the completed transcript with prepare_episode.py <canonical-url> --output-dir <same-directory> --transcript <file>"]
    except Exception as exc:
        result["status"] = "partial" if result["source"] else "blocked"
        result["warnings"].append({"stage": stage, "message": redact_remote_urls(str(exc))})
        result["next_actions"] = ["Resolve the reported dependency, selection or public-access issue; do not add cookies or bypass access controls"]
    finally:
        for path in temporary:
            path.unlink(missing_ok=True)
    atomic_write_json(output_dir / "ingest-result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="BV ID or canonical Bilibili video URL; ?p=N selects one part")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--page", type=int, help="Explicit 1-based part; required for multi-part videos unless URL has ?p=N")
    parser.add_argument("--mode", choices=("metadata", "audio"), default="audio")
    parser.add_argument("--max-duration-minutes", type=float, default=480, help="Limit the selected part; 0 explicitly disables the upper bound")
    parser.add_argument("--max-bytes", type=int, default=MAX_BYTES)
    parser.add_argument("--timeout", type=float, default=60, help="Timeout in seconds for each metadata/stream lookup")
    parser.add_argument("--force", action="store_true", help="Refresh audio atomically; preserve any existing file if acquisition fails")
    args = parser.parse_args()
    result = asyncio.run(acquire(args.input, Path(args.output_dir), page=args.page, mode=args.mode,
                                 max_duration_minutes=args.max_duration_minutes, max_bytes=args.max_bytes,
                                 timeout=args.timeout, force=args.force))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"ready", "metadata_only"} else 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
