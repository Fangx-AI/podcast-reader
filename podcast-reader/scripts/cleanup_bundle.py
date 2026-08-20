#!/usr/bin/env python3
"""Preview or apply safe Podcast Reader cache/media cleanup with an audit manifest."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
from typing import Any

from runtime_utils import atomic_write_json


CACHE_DIRS = {"audio-chunks", "chunk-transcripts", ".invalid-cache"}
MEDIA_EXTENSIONS = {".mp3", ".m4a", ".mp4", ".wav", ".aac", ".ogg", ".opus", ".flac", ".webm", ".mkv", ".mov"}
PRESERVE = {"transcript.json", "transcript.md", "transcript.srt", "transcript.vtt", "chunks.json", "analysis.md", "summary.md", "evidence.json", "bundle.json", "source.json", "reader.html"}


def candidates(episode_dir: Path, scope: str) -> list[Path]:
    selected: set[Path] = set()
    if scope in {"cache", "all"}:
        for name in CACHE_DIRS:
            path = episode_dir / name
            if path.exists():
                selected.add(path)
        for path in episode_dir.rglob("*.part"):
            selected.add(path)
    if scope in {"media", "all"}:
        for path in episode_dir.iterdir():
            if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS and path.name not in PRESERVE:
                selected.add(path)
    return sorted(selected, key=lambda path: (len(path.parts), str(path)), reverse=True)


def path_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def cleanup(episode_dir: Path, scope: str, apply: bool) -> dict[str, Any]:
    episode_dir = episode_dir.expanduser().resolve()
    if not (episode_dir / "bundle.json").is_file():
        raise FileNotFoundError("cleanup requires an episode directory containing bundle.json")
    targets = candidates(episode_dir, scope)
    records = []
    for target in targets:
        resolved = target.resolve()
        try:
            relative = resolved.relative_to(episode_dir)
        except ValueError as exc:
            raise RuntimeError(f"cleanup target escapes episode directory: {resolved}") from exc
        records.append({"path": relative.as_posix(), "type": "directory" if target.is_dir() else "file", "size_bytes": path_size(target)})
    total = sum(item["size_bytes"] for item in records)
    if apply:
        for target in targets:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink(missing_ok=True)
    result = {
        "schema_version": "2.0", "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "applied" if apply else "preview", "scope": scope,
        "episode_dir": str(episode_dir), "targets": records,
        "bytes_reclaimable": total, "mib_reclaimable": round(total / (1024 ** 2), 2),
        "knowledge_artifacts_preserved": sorted(PRESERVE),
    }
    if apply:
        atomic_write_json(episode_dir / "cleanup-manifest.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode_dir")
    parser.add_argument("--scope", choices=("cache", "media", "all"), default="cache")
    parser.add_argument("--apply", action="store_true", help="Apply the previewed cleanup; default is read-only")
    args = parser.parse_args()
    try:
        result = cleanup(Path(args.episode_dir), args.scope, args.apply)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
