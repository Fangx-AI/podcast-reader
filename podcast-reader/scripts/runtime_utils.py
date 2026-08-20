#!/usr/bin/env python3
"""Shared reliability, security, and portability helpers for Podcast Reader."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
from pathlib import Path
import socket
import tempfile
from typing import Any
import urllib.parse
import urllib.request
import argparse


SCHEMA_VERSION = "2.0"
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent


def skill_version() -> str:
    return (SKILL_DIR / "VERSION").read_text(encoding="utf-8").strip()


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def load_json_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def sha256_file(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def file_fingerprint(path: Path, include_hash: bool = True) -> dict[str, Any]:
    path = path.expanduser().resolve()
    stat = path.stat()
    result: dict[str, Any] = {
        "name": path.name,
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }
    if include_hash:
        result["sha256"] = sha256_file(path)
    return result


def same_fingerprint(left: Any, right: Any) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    fields = ("size_bytes", "mtime_ns", "sha256")
    return all(left.get(field) == right.get(field) for field in fields)


def portable_path(path: Path, root: Path) -> str:
    path = path.expanduser().resolve()
    root = root.expanduser().resolve()
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _public_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%", 1)[0])
    return ip.is_global


def validate_public_http_url(url: str, allow_private: bool = False) -> str:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("only http(s) URLs are supported")
    if parsed.username or parsed.password:
        raise ValueError("credentials in URLs are not allowed")
    if not parsed.hostname:
        raise ValueError("URL hostname is missing")
    if allow_private:
        return url
    host = parsed.hostname.rstrip(".").casefold()
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("private or loopback network targets are not allowed")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ValueError(f"hostname could not be resolved: {host}") from exc
    if not addresses or any(not _public_ip(address) for address in addresses):
        raise ValueError("private, loopback, link-local, or reserved network targets are not allowed")
    return url


class PublicRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, allow_private: bool = False) -> None:
        super().__init__()
        self.allow_private = allow_private

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        validate_public_http_url(newurl, self.allow_private)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def safe_urlopen(request: str | urllib.request.Request, timeout: int = 60, allow_private: bool = False):
    url = request.full_url if isinstance(request, urllib.request.Request) else request
    validate_public_http_url(url, allow_private)
    opener = urllib.request.build_opener(PublicRedirectHandler(allow_private))
    response = opener.open(request, timeout=timeout)
    try:
        validate_public_http_url(response.geturl(), allow_private)
    except Exception:
        response.close()
        raise
    return response


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print("Podcast Reader runtime utility module; import it from other bundled scripts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
