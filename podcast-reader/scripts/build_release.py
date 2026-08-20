#!/usr/bin/env python3
"""Build a deterministic, prefixed release ZIP, SBOM, and SHA-256 sidecars."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

from generate_sbom import generate as generate_sbom
from release_check import check as release_check
from runtime_utils import atomic_write_text, sha256_file, skill_version


ROOT = Path(__file__).resolve().parents[2]
EXCLUDED_PARTS = {".git", "dist", "__pycache__", ".pytest_cache", "outputs"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".part", ".mp3", ".m4a", ".mp4", ".wav", ".ogg", ".opus", ".flac", ".webm", ".mkv", ".mov"}


def release_files() -> list[Path]:
    return sorted(
        path for path in ROOT.rglob("*")
        if path.is_file()
        and not EXCLUDED_PARTS.intersection(path.relative_to(ROOT).parts)
        and path.suffix.casefold() not in EXCLUDED_SUFFIXES
    )


def run_check(command: list[str]) -> None:
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        raise RuntimeError(f"release validation failed: {' '.join(command)}")


def build(output_dir: Path, skip_tests: bool) -> dict:
    result = release_check()
    if not result["valid"]:
        raise RuntimeError("release_check failed: " + "; ".join(result["errors"]))
    if not skip_tests:
        run_check([sys.executable, "-m", "compileall", "-q", "podcast-reader/scripts"])
        run_check([sys.executable, "-m", "unittest", "discover", "-s", "podcast-reader/tests", "-v"])
    version = skill_version()
    output_dir.mkdir(parents=True, exist_ok=True)
    sbom = output_dir / f"podcast-reader-{version}.sbom.json"
    generate_sbom(sbom)
    archive_path = output_dir / f"podcast-reader-{version}.zip"
    with tempfile.NamedTemporaryFile(prefix=".release-", suffix=".zip", dir=output_dir, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in [*release_files(), sbom]:
                relative = path.relative_to(ROOT) if path.is_relative_to(ROOT) else Path("dist") / path.name
                info = zipfile.ZipInfo(f"podcast-reader-{version}/{relative.as_posix()}", date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, path.read_bytes())
        os.replace(temporary, archive_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    digest = sha256_file(archive_path)
    checksum = archive_path.with_suffix(".zip.sha256")
    atomic_write_text(checksum, f"{digest}  {archive_path.name}\n")
    return {"status": "built", "version": version, "archive": str(archive_path), "sha256": digest, "checksum": str(checksum), "sbom": str(sbom), "files": len(release_files()) + 1}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="dist")
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()
    try:
        result = build(Path(args.output_dir).expanduser().resolve(), args.skip_tests)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
