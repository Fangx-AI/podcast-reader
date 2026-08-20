#!/usr/bin/env python3
"""Export evidence.json collections to Excel-friendly UTF-8 CSV files."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


COLLECTIONS = ("chapters", "claims", "quotes", "actions", "entities", "glossary", "visual_evidence")


def flatten(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    if isinstance(value, list):
        return "; ".join(flatten(item) for item in value)
    if isinstance(value, dict):
        if value.get("start") or value.get("end"):
            span = str(value.get("start") or "")
            if value.get("end") and value.get("end") != value.get("start"):
                span += f"–{value['end']}"
            label = value.get("label")
            return f"{span} ({label})" if label else span
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def export_collection(name: str, rows: list[dict[str, Any]], output_dir: Path) -> Path | None:
    if not rows:
        return None
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    target = output_dir / f"{name}.csv"
    with target.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: flatten(row.get(key)) for key in fields})
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_json")
    parser.add_argument("--output-dir")
    parser.add_argument("--only", choices=COLLECTIONS, action="append")
    args = parser.parse_args()
    source = Path(args.evidence_json).expanduser().resolve()
    data = json.loads(source.read_text(encoding="utf-8-sig"))
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else source.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    selected = args.only or COLLECTIONS
    exports = {}
    for name in selected:
        rows = data.get(name, []) if isinstance(data, dict) else []
        if isinstance(rows, list):
            target = export_collection(name, [row for row in rows if isinstance(row, dict)], output_dir)
            if target:
                exports[name] = str(target)
    print(json.dumps({"status": "ready", "source": str(source), "exports": exports}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
