#!/usr/bin/env python3
"""Validate version, documentation, links, scripts, and release invariants."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from runtime_utils import skill_version


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "podcast-reader"


def check() -> dict:
    version = skill_version()
    errors: list[str] = []
    warnings: list[str] = []
    skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    metadata_match = re.search(r'(?m)^\s*version:\s*["\']?([^"\'\s]+)', skill_text)
    if not metadata_match or metadata_match.group(1) != version:
        errors.append("SKILL.md metadata version does not match VERSION")
    if not readme.startswith(f"# Podcast Reader v{version}"):
        errors.append("README.md title version does not match VERSION")
    release_doc = ROOT / "docs" / f"release-v{version}.md"
    if not release_doc.is_file():
        errors.append(f"release document is missing: {release_doc.name}")
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", skill_text)
    for link in links:
        if "://" in link or link.startswith("#"):
            continue
        target = (SKILL / link.split("#", 1)[0]).resolve()
        try:
            target.relative_to(SKILL.resolve())
        except ValueError:
            errors.append(f"SKILL.md link escapes skill directory: {link}")
            continue
        if not target.exists():
            errors.append(f"SKILL.md link is missing: {link}")
    pycache = [path for path in SKILL.rglob("__pycache__")]
    if pycache:
        warnings.append(f"{len(pycache)} __pycache__ directories exist locally and must be excluded from release")
    forbidden = [path for path in ROOT.rglob("*.part") if ".git" not in path.parts]
    if forbidden:
        errors.append("incomplete .part files exist in the repository")
    scripts = sorted((SKILL / "scripts").glob("*.py"))
    tests = len(re.findall(r"(?m)^\s*def test_", "\n".join(path.read_text(encoding="utf-8") for path in (SKILL / "tests").glob("test_*.py"))))
    return {"valid": not errors, "version": version, "errors": errors, "warnings": warnings, "metrics": {"scripts": len(scripts), "tests": tests, "skill_lines": len(skill_text.splitlines()), "skill_links": len(links)}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    result = check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
