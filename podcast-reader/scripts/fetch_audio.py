#!/usr/bin/env python3
"""Download one public direct media URL with bounded size and atomic completion."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path


MEDIA_EXTENSIONS = {".mp3", ".m4a", ".mp4", ".wav", ".aac", ".ogg", ".opus", ".flac", ".webm"}
USER_AGENT = "podcast-reader/2.0"


def safe_name(value: str) -> str:
    value = re.sub(r"[^\w\-. ]+", "", value, flags=re.UNICODE).strip().replace(" ", "-")
    return value[:100].strip(".-") or "podcast-episode"


def infer_suffix(url: str, content_type: str) -> str:
    suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if suffix in MEDIA_EXTENSIONS:
        return suffix
    mapping = {
        "audio/mpeg": ".mp3", "audio/mp4": ".m4a", "audio/x-m4a": ".m4a",
        "audio/ogg": ".ogg", "audio/opus": ".opus", "audio/flac": ".flac",
        "audio/wav": ".wav", "video/mp4": ".mp4", "video/webm": ".webm",
    }
    return mapping.get(content_type.split(";", 1)[0].strip().lower(), ".mp3")


def public_source_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    return urllib.parse.urlunsplit((parsed.scheme, host + port, parsed.path, "", ""))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--output-dir", default="outputs/podcast-reader/audio")
    parser.add_argument("--name", help="Base filename without extension")
    parser.add_argument("--max-mb", type=int, default=2048, help="Maximum download size; 0 disables")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    parsed = urllib.parse.urlparse(args.url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("only http(s) URLs are supported")
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(args.url, headers={"User-Agent": USER_AGENT, "Accept": "audio/*,video/*;q=0.8,*/*;q=0.1"})
    max_bytes = args.max_mb * 1024 * 1024 if args.max_mb else 0

    target: Path | None = None
    partial: Path | None = None
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content_type = response.headers.get("Content-Type", "")
            media_type = content_type.split(";", 1)[0].strip().lower()
            if media_type.startswith("text/") or media_type in {"application/json", "application/xml", "application/xhtml+xml"}:
                raise ValueError(f"remote response is not media: {media_type or 'unknown content type'}")
            content_length = int(response.headers.get("Content-Length", "0") or 0)
            if max_bytes and content_length > max_bytes:
                raise ValueError(f"declared file size {content_length} exceeds --max-mb {args.max_mb}")
            suffix = infer_suffix(response.geturl(), content_type)
            default_stem = Path(parsed.path).stem or "podcast-episode"
            url_suffix = hashlib.sha256(args.url.encode("utf-8")).hexdigest()[:10]
            base = safe_name(args.name) if args.name else f"{safe_name(default_stem)}-{url_suffix}"
            target = output_dir / f"{base}{suffix}"
            partial = target.with_suffix(target.suffix + ".part")
            if target.exists() and not args.force:
                result = {"status": "cached", "path": str(target), "size_bytes": target.stat().st_size, "source_url": public_source_url(args.url)}
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0
            digest = hashlib.sha256()
            total = 0
            with partial.open("wb") as handle:
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if max_bytes and total > max_bytes:
                        raise ValueError(f"download exceeded --max-mb {args.max_mb}")
                    digest.update(chunk)
                    handle.write(chunk)
            if total == 0:
                raise ValueError("remote server returned an empty file")
            partial.replace(target)
        result = {
            "status": "downloaded",
            "path": str(target),
            "size_bytes": target.stat().st_size,
            "sha256": digest.hexdigest(),
            "source_url": public_source_url(args.url),
            "content_type": content_type,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        if partial and partial.exists():
            partial.unlink()
        print(json.dumps({"status": "blocked", "stage": "download", "source_url": public_source_url(args.url), "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
