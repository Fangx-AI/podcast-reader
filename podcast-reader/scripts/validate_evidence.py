#!/usr/bin/env python3
"""Validate evidence.json against transcript segments, timestamps, enums, and exact quotes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from evidence_validator import validate_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence")
    parser.add_argument("--transcript", required=True)
    args = parser.parse_args()
    evidence_path = Path(args.evidence).expanduser().resolve()
    transcript_path = Path(args.transcript).expanduser().resolve()
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
        transcript = json.loads(transcript_path.read_text(encoding="utf-8-sig"))
        result = validate_evidence(evidence, transcript)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        result = {"valid": False, "errors": [str(exc)], "warnings": []}
    result.update({"evidence": str(evidence_path), "transcript": str(transcript_path)})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
