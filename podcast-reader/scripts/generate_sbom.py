#!/usr/bin/env python3
"""Generate a CycloneDX JSON SBOM with hashes for the release source tree."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import uuid

from runtime_utils import atomic_write_json, sha256_file, skill_version


ROOT = Path(__file__).resolve().parents[2]
EXCLUDED_PARTS = {".git", "dist", "__pycache__", ".pytest_cache"}


def files() -> list[Path]:
    return sorted(
        path for path in ROOT.rglob("*")
        if path.is_file()
        and not EXCLUDED_PARTS.intersection(path.relative_to(ROOT).parts)
        and path.suffix not in {".pyc", ".pyo"}
    )


def generate(output: Path) -> dict:
    version = skill_version()
    components = [
        {"type": "file", "name": path.relative_to(ROOT).as_posix(), "hashes": [{"alg": "SHA-256", "content": sha256_file(path)}]}
        for path in files()
    ]
    identity = "\n".join(f"{item['name']}:{item['hashes'][0]['content']}" for item in components)
    serial = uuid.uuid5(uuid.NAMESPACE_URL, f"podcast-reader:{version}:{identity}")
    document = {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{serial}", "version": 1,
        "metadata": {
            "component": {"type": "application", "name": "podcast-reader", "version": version, "licenses": [{"license": {"id": "MIT"}}]},
            "tools": {"components": [{"type": "application", "name": "podcast-reader-generate-sbom", "version": version}]},
        },
        "components": components,
        "properties": [
            {"name": "podcast-reader:runtime", "value": "Python 3.10+"},
            {"name": "podcast-reader:optional-transcription", "value": "faster-whisper==1.2.1"},
            {"name": "podcast-reader:optional-ingestion", "value": "yt-dlp==2026.08.19 via uv bootstrap; installed command may differ"},
        ],
    }
    atomic_write_json(output, document)
    return {"status": "generated", "output": str(output), "components": len(components), "version": version}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output")
    args = parser.parse_args()
    output = Path(args.output).expanduser().resolve() if args.output else ROOT / "dist" / f"podcast-reader-{skill_version()}.sbom.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    result = generate(output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
