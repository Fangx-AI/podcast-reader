#!/usr/bin/env python3
"""Install Podcast Reader into a Codex or Agent Skills directory."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import uuid
from typing import Any


SKILL_NAME = "podcast-reader"
SOURCE = Path(__file__).resolve().parents[1]


def default_target_root() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    return (Path(codex_home).expanduser() / "skills") if codex_home else (Path.home() / ".codex" / "skills")


def ignore_install_files(_directory: str, names: list[str]) -> set[str]:
    ignored = {name for name in names if name == "__pycache__" or name.endswith((".pyc", ".pyo"))}
    return ignored


def install(target_root: Path, force: bool) -> dict[str, Any]:
    target_root = target_root.expanduser().resolve()
    destination = target_root / SKILL_NAME
    if SOURCE.resolve() == destination.resolve():
        return {"status": "already_installed", "destination": str(destination), "backup": None, "valid": True}
    if not (SOURCE / "SKILL.md").is_file():
        return {"status": "blocked", "error": f"source SKILL.md is missing: {SOURCE}", "valid": False}
    target_root.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        return {
            "status": "blocked",
            "error": f"destination already exists: {destination}",
            "next_actions": ["rerun with --force to replace it while preserving a timestamped backup"],
            "valid": False,
        }

    temporary = target_root / f".{SKILL_NAME}.install-{uuid.uuid4().hex[:8]}"
    backup: Path | None = None
    try:
        shutil.copytree(SOURCE, temporary, ignore=ignore_install_files)
        if not (temporary / "SKILL.md").is_file() or not (temporary / "scripts" / "doctor.py").is_file():
            raise RuntimeError("copied skill failed structural verification")
        if destination.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = target_root / f"{SKILL_NAME}.backup-{stamp}"
            suffix = 1
            while backup.exists():
                backup = target_root / f"{SKILL_NAME}.backup-{stamp}-{suffix}"
                suffix += 1
            destination.replace(backup)
        temporary.replace(destination)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)
        if backup and backup.exists() and not destination.exists():
            backup.replace(destination)
        raise

    return {
        "status": "installed",
        "destination": str(destination),
        "backup": str(backup) if backup else None,
        "valid": True,
        "next_actions": [
            f'python "{destination / "scripts" / "doctor.py"}" --json',
            "Restart or refresh the Agent if it does not discover newly installed skills automatically.",
        ],
    }


def human(result: dict[str, Any]) -> str:
    if result.get("valid"):
        lines = [f"Podcast Reader: {result['status']}", f"Destination: {result['destination']}"]
        if result.get("backup"):
            lines.append(f"Previous installation backup: {result['backup']}")
        if result.get("next_actions"):
            lines.append("Next:")
            lines.extend(f"- {item}" for item in result["next_actions"])
        return "\n".join(lines)
    return f"Podcast Reader installation blocked: {result.get('error')}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default=str(default_target_root()), help="Parent Skills directory; podcast-reader/ is created inside it")
    parser.add_argument("--force", action="store_true", help="Replace an existing installation and preserve it as a timestamped backup")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = install(Path(args.target), args.force)
    except Exception as exc:
        result = {"status": "blocked", "error": str(exc), "valid": False}
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else human(result))
    return 0 if result.get("valid") else 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
