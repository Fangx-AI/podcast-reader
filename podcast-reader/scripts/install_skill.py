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

from runtime_utils import skill_version


SKILL_NAME = "podcast-reader"
SOURCE = Path(__file__).resolve().parents[1]
DEVELOPER_ONLY_SCRIPTS = {"build_release.py", "generate_sbom.py", "release_check.py"}


def version_at(folder: Path) -> str | None:
    path = folder / "VERSION"
    return path.read_text(encoding="utf-8").strip() if path.is_file() else None


def version_tuple(value: str | None) -> tuple[int, ...]:
    if not value:
        return ()
    try:
        return tuple(int(part) for part in value.split(".")[:3])
    except ValueError:
        return ()


def backups(target_root: Path) -> list[Path]:
    target_root = target_root.expanduser().resolve()
    return sorted(
        [path for path in target_root.glob(f"{SKILL_NAME}.backup-*") if path.is_dir()],
        key=lambda path: (path.stat().st_mtime_ns, path.name), reverse=True,
    )


def prune_backups(target_root: Path, keep: int) -> list[str]:
    removed = []
    for path in backups(target_root)[max(0, keep):]:
        path.relative_to(target_root.expanduser().resolve())
        shutil.rmtree(path)
        removed.append(str(path))
    return removed


def rollback(target_root: Path, requested: str) -> dict[str, Any]:
    target_root = target_root.expanduser().resolve()
    destination = target_root / SKILL_NAME
    available = backups(target_root)
    if not available:
        return {"status": "blocked", "error": "no Podcast Reader installation backups were found", "valid": False}
    if requested == "latest":
        selected = available[0]
    else:
        selected = (target_root / requested).resolve()
        selected.relative_to(target_root)
        if selected not in available:
            return {"status": "blocked", "error": f"backup not found: {requested}", "valid": False}
    if not (selected / "SKILL.md").is_file():
        return {"status": "blocked", "error": f"backup is invalid: {selected}", "valid": False}
    displaced = None
    if destination.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        displaced = target_root / f"{SKILL_NAME}.backup-rollback-from-{stamp}"
        destination.replace(displaced)
    try:
        selected.replace(destination)
    except Exception:
        if displaced and displaced.exists() and not destination.exists():
            displaced.replace(destination)
        raise
    return {"status": "rolled_back", "destination": str(destination), "version": version_at(destination), "previous_installation": str(displaced) if displaced else None, "valid": True}


def default_target_root() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    return (Path(codex_home).expanduser() / "skills") if codex_home else (Path.home() / ".codex" / "skills")


def ignore_install_files(_directory: str, names: list[str]) -> set[str]:
    ignored = {name for name in names if name == "__pycache__" or name.endswith((".pyc", ".pyo"))}
    directory = Path(_directory).resolve()
    if directory == SOURCE.resolve() and "tests" in names:
        ignored.add("tests")
    if directory == (SOURCE / "scripts").resolve():
        ignored.update(name for name in DEVELOPER_ONLY_SCRIPTS if name in names)
    return ignored


def install(target_root: Path, force: bool, allow_downgrade: bool = False, keep_backups: int = 3) -> dict[str, Any]:
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
    source_version = version_at(SOURCE) or skill_version()
    installed_version = version_at(destination) if destination.exists() else None
    if destination.exists() and version_tuple(installed_version) > version_tuple(source_version) and not allow_downgrade:
        return {
            "status": "blocked", "valid": False,
            "error": f"refusing downgrade from {installed_version} to {source_version}",
            "next_actions": ["rerun with --allow-downgrade only when the older version is intentional"],
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

    removed_backups = prune_backups(target_root, keep_backups)
    return {
        "status": "installed",
        "version": source_version,
        "replaced_version": installed_version,
        "destination": str(destination),
        "backup": str(backup) if backup else None,
        "valid": True,
        "removed_old_backups": removed_backups,
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
    parser.add_argument("--allow-downgrade", action="store_true", help="Allow replacing a newer installed version with this older source")
    parser.add_argument("--keep-backups", type=int, default=3, help="Retain this many newest timestamped backups after an install")
    parser.add_argument("--list-backups", action="store_true")
    parser.add_argument("--rollback", nargs="?", const="latest", help="Restore the latest backup or a named backup directory")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        target = Path(args.target)
        if args.keep_backups < 0:
            parser.error("--keep-backups cannot be negative")
        if args.list_backups:
            result = {"status": "listed", "valid": True, "backups": [{"name": path.name, "path": str(path), "version": version_at(path)} for path in backups(target)]}
        elif args.rollback:
            result = rollback(target, args.rollback)
        else:
            result = install(target, args.force, args.allow_downgrade, args.keep_backups)
    except Exception as exc:
        result = {"status": "blocked", "error": str(exc), "valid": False}
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else human(result))
    return 0 if result.get("valid") else 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
