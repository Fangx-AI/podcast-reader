#!/usr/bin/env python3
"""Classify and resolve podcast, feed, webpage, media URL, or local input.

The resolver uses only the Python standard library, reads at most a bounded
amount of remote content, and never attempts authentication or access-control
bypass. Results are JSON so the script can be used by agents and pipelines.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import html
from html.parser import HTMLParser
import json
import mimetypes
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


MEDIA_EXTENSIONS = {
    ".mp3", ".m4a", ".mp4", ".wav", ".aac", ".ogg", ".opus",
    ".flac", ".webm", ".mkv", ".mov",
}
TRANSCRIPT_EXTENSIONS = {".srt", ".vtt", ".txt", ".md", ".json"}
FEED_EXTENSIONS = {".xml", ".rss", ".atom"}
USER_AGENT = "podcast-reader/2.0 (+https://github.com/openai/codex)"


def fetch(url: str, limit: int = 3_000_000, timeout: int = 25) -> tuple[bytes, str, str]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, text/html, */*;q=0.5"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        final_url = response.geturl()
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"response exceeds safety limit of {limit} bytes")
    return data, content_type, final_url


def safe_output(value: Any, key: str = "") -> Any:
    if isinstance(value, dict):
        return {item_key: safe_output(item_value, item_key) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [safe_output(item, key) for item in value]
    if isinstance(value, str) and value.startswith(("http://", "https://")) and any(term in key.casefold() for term in ("audio", "media", "transcript")):
        parsed = urllib.parse.urlsplit(value)
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        return urllib.parse.urlunsplit((parsed.scheme, host + port, parsed.path, "", ""))
    return value


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _node_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def _first_text(parent: ET.Element, names: set[str]) -> str:
    for child in list(parent):
        if _local_name(child.tag) in names:
            value = _node_text(child)
            if value:
                return value
    return ""


def _published_timestamp(value: str) -> float | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def parse_rss(data: bytes, url: str, query: str | None = None, latest: bool = False) -> dict[str, Any]:
    root = ET.fromstring(data)
    if _local_name(root.tag) not in {"rss", "feed", "rdf"}:
        raise ValueError("not an RSS, Atom, or RDF feed")

    channel = next((node for node in root.iter() if _local_name(node.tag) in {"channel", "feed"}), root)
    feed_title = _first_text(channel, {"title"})
    items = [node for node in root.iter() if _local_name(node.tag) in {"item", "entry"}]
    episodes: list[dict[str, Any]] = []
    for position, item in enumerate(items):
        title = _first_text(item, {"title"})
        guid = _first_text(item, {"guid", "id"})
        date = _first_text(item, {"pubdate", "published", "updated", "date"})
        description = _first_text(item, {"description", "summary", "content", "encoded"})
        duration = _first_text(item, {"duration"})
        audio_url = ""
        episode_url = ""
        transcript_urls: list[str] = []
        for child in item.iter():
            tag = _local_name(child.tag)
            href = child.attrib.get("href") or child.attrib.get("url") or ""
            media_type = child.attrib.get("type", "").lower()
            rel = child.attrib.get("rel", "").lower()
            if tag == "enclosure" and href and (media_type.startswith("audio/") or Path(urllib.parse.urlparse(href).path).suffix.lower() in MEDIA_EXTENSIONS):
                audio_url = urllib.parse.urljoin(url, href)
            elif tag == "link" and href:
                joined = urllib.parse.urljoin(url, href)
                if media_type.startswith("audio/") and not audio_url:
                    audio_url = joined
                elif rel in {"alternate", ""} and not episode_url:
                    episode_url = joined
            elif tag == "transcript" and href:
                transcript_urls.append(urllib.parse.urljoin(url, href))
        episodes.append({
            "position": position,
            "title": title,
            "guid": guid,
            "published": date,
            "duration": duration or None,
            "episode_url": episode_url or None,
            "audio_url": audio_url or None,
            "transcript_urls": transcript_urls,
            "description": html.unescape(re.sub(r"<[^>]+>", " ", description)).strip(),
        })

    selected: list[dict[str, Any]] = []
    if query:
        needle = query.casefold().strip()
        exact = [item for item in episodes if needle in {item["title"].casefold(), item["guid"].casefold()}]
        selected = exact or [item for item in episodes if needle in item["title"].casefold() or needle in item["guid"].casefold()]
    elif latest and episodes:
        dated = [(timestamp, item) for item in episodes if (timestamp := _published_timestamp(str(item.get("published") or ""))) is not None]
        selected = [max(dated, key=lambda pair: pair[0])[1] if dated else episodes[0]]
    elif len(episodes) == 1:
        selected = episodes

    result: dict[str, Any] = {
        "kind": "rss",
        "source_url": url,
        "feed_title": feed_title,
        "episode_count": len(episodes),
        "candidates": (selected or episodes)[:20],
    }
    if len(selected) == 1:
        result["episode"] = selected[0]
        result["audio_url"] = selected[0]["audio_url"]
        result["transcript_urls"] = selected[0]["transcript_urls"]
    elif query and not selected:
        result["warning"] = f"no episode matched query: {query}"
    elif len(selected) > 1:
        result["warning"] = "episode query is ambiguous; choose one candidate"
    return result


class EpisodeHTMLParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.in_title = False
        self.title_parts: list[str] = []
        self.meta: dict[str, list[str]] = {}
        self.audio_candidates: list[str] = []
        self.feed_candidates: list[str] = []
        self.transcript_candidates: list[str] = []
        self.json_ld: list[str] = []
        self._json_buffer: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        tag = tag.lower()
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            content = values.get("content", "").strip()
            if key and content:
                self.meta.setdefault(key, []).append(content)
                if key in {"og:audio", "og:audio:url", "twitter:player:stream"}:
                    self.audio_candidates.append(urllib.parse.urljoin(self.base_url, content))
        elif tag in {"audio", "source"} and values.get("src"):
            media_type = values.get("type", "").lower()
            if tag == "audio" or not media_type or media_type.startswith(("audio/", "video/")):
                self.audio_candidates.append(urllib.parse.urljoin(self.base_url, values["src"]))
        elif tag == "link" and values.get("href"):
            href = urllib.parse.urljoin(self.base_url, values["href"])
            media_type = values.get("type", "").lower()
            rel = values.get("rel", "").lower()
            if media_type in {"application/rss+xml", "application/atom+xml"}:
                self.feed_candidates.append(href)
            elif media_type.startswith(("audio/", "video/")):
                self.audio_candidates.append(href)
            elif "transcript" in rel or Path(urllib.parse.urlparse(href).path).suffix.lower() in TRANSCRIPT_EXTENSIONS:
                self.transcript_candidates.append(href)
        elif tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self._json_buffer = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        elif tag == "script" and self._json_buffer is not None:
            self.json_ld.append("".join(self._json_buffer))
            self._json_buffer = None

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self._json_buffer is not None:
            self._json_buffer.append(data)


def _walk_json(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_json(child)


def parse_html(data: bytes, url: str) -> dict[str, Any]:
    raw = data.decode("utf-8", errors="replace")
    parser = EpisodeHTMLParser(url)
    parser.feed(raw)
    title = (parser.meta.get("og:title") or [" ".join(parser.title_parts).strip()])[0]
    duration: str | int | None = (parser.meta.get("music:duration") or parser.meta.get("video:duration") or [None])[0]
    for block in parser.json_ld:
        try:
            parsed = json.loads(block)
        except (json.JSONDecodeError, TypeError):
            continue
        for node in _walk_json(parsed):
            node_type = node.get("@type")
            node_types = {str(x).lower() for x in (node_type if isinstance(node_type, list) else [node_type]) if x}
            if node_types & {"podcastepisode", "audioobject", "videoobject", "episode"}:
                title = title or str(node.get("name") or "")
                duration = duration or node.get("duration")
                for key in ("contentUrl", "embedUrl"):
                    candidate = node.get(key)
                    if isinstance(candidate, str):
                        parser.audio_candidates.append(urllib.parse.urljoin(url, candidate))
                transcript = node.get("transcript")
                if isinstance(transcript, str) and transcript.startswith(("http://", "https://")):
                    parser.transcript_candidates.append(transcript)

    unique = lambda values: list(dict.fromkeys(value for value in values if value))
    audio = unique(parser.audio_candidates)
    feeds = unique(parser.feed_candidates)
    transcripts = unique(parser.transcript_candidates)
    result: dict[str, Any] = {
        "kind": "episode_page",
        "source_url": url,
        "title": html.unescape(title).strip(),
        "duration": duration,
        "audio_candidates": audio,
        "transcript_candidates": transcripts,
        "feed_candidates": feeds,
    }
    if len(audio) == 1:
        result["audio_url"] = audio[0]
    if not audio and not transcripts and not feeds:
        result["warning"] = "no public audio, transcript, or feed link found in page metadata"
    return result


def resolve_input(value: str, query: str | None = None, no_network: bool = False, latest: bool = False) -> dict[str, Any]:
    value = value.strip()
    local = Path(value).expanduser()
    if local.exists():
        resolved = local.resolve()
        extension = local.suffix.lower()
        if extension in FEED_EXTENSIONS:
            try:
                result = parse_rss(local.read_bytes(), resolved.as_uri(), query, latest)
                result["kind"] = "local_rss"
                result["path"] = str(resolved)
                return result
            except (ET.ParseError, ValueError) as exc:
                return {"kind": "local_file", "path": str(resolved), "extension": extension, "warning": f"feed parse failed: {exc}"}
        if extension in TRANSCRIPT_EXTENSIONS:
            kind = "local_transcript"
        elif extension in MEDIA_EXTENSIONS:
            kind = "local_media"
        else:
            kind = "local_file"
        return {"kind": kind, "path": str(resolved), "extension": extension, "size_bytes": local.stat().st_size}

    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return {"kind": "unknown", "input": value, "error": "expected an existing local path or http(s) URL"}
    host = parsed.netloc.casefold().split(":", 1)[0]
    extension = Path(parsed.path).suffix.lower()
    if extension in MEDIA_EXTENSIONS:
        guessed_type, _ = mimetypes.guess_type(parsed.path)
        return {"kind": "media_url", "source_url": value, "media_url": value, "content_type": guessed_type}
    if host == "youtu.be" or host.endswith("youtube.com"):
        return {"kind": "youtube", "source_url": value, "adapter": "yt-dlp", "strategy": "subtitle-first"}
    if host == "b23.tv" or host.endswith("bilibili.com"):
        return {"kind": "bilibili", "source_url": value, "adapter": "yt-dlp", "strategy": "subtitle-first"}
    if no_network:
        return {"kind": "web_url", "source_url": value, "next_action": "inspect public feed, transcript, and media metadata"}

    try:
        data, content_type, final_url = fetch(value)
        lowered = content_type.lower()
        if lowered.startswith(("audio/", "video/")):
            return {"kind": "media_url", "source_url": value, "canonical_url": final_url, "media_url": final_url, "content_type": content_type}
        try:
            result = parse_rss(data, final_url, query, latest)
        except (ET.ParseError, ValueError):
            result = parse_html(data, final_url)
        if final_url != value:
            result["requested_url"] = value
        return result
    except Exception as exc:  # Network failures are data, not tracebacks, for callers.
        return {"kind": "unresolved", "source_url": value, "error": str(exc), "next_action": "provide a direct media, transcript, or feed URL"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="URL, RSS/Atom feed, or local file")
    parser.add_argument("--query", help="Episode title or GUID when input is a feed")
    parser.add_argument("--latest", action="store_true", help="Select the first feed item as latest")
    parser.add_argument("--no-network", action="store_true", help="Classify without fetching generic URLs")
    args = parser.parse_args()
    result = resolve_input(args.input, args.query, args.no_network, args.latest)
    stream = sys.stderr if result.get("kind") in {"unknown", "unresolved"} else sys.stdout
    print(json.dumps(safe_output(result), ensure_ascii=False, indent=2), file=stream)
    return 2 if result.get("kind") == "unknown" else 1 if result.get("kind") == "unresolved" else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
