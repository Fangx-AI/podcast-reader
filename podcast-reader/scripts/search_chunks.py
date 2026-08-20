#!/usr/bin/env python3
"""Search a podcast chunk index with dependency-free multilingual ranking."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


LATIN_TERM = re.compile(r"[A-Za-z0-9_+#.-]{2,}")
CJK_RUN = re.compile(r"[\u3400-\u9fff]+")


def terms(value: str) -> list[str]:
    value = value.casefold()
    result = LATIN_TERM.findall(value)
    for run in CJK_RUN.findall(value):
        result.extend(run[index:index + 2] for index in range(max(1, len(run) - 1)))
        if len(run) <= 4:
            result.append(run)
    return list(dict.fromkeys(term for term in result if term))


def rank(chunks: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    query_terms = terms(query)
    lowered_query = query.casefold().strip()
    document_frequency = {term: sum(term in str(chunk.get("search_text") or chunk.get("text") or "").casefold() for chunk in chunks) for term in query_terms}
    ranked = []
    for chunk in chunks:
        haystack = str(chunk.get("search_text") or chunk.get("text") or "").casefold()
        score = 0.0
        matched = []
        for term in query_terms:
            count = haystack.count(term)
            if count:
                inverse = math.log((len(chunks) + 1) / (document_frequency[term] + 0.5)) + 1
                score += (1 + math.log(count)) * inverse
                matched.append(term)
        if lowered_query and lowered_query in haystack:
            score += 8.0
        if score:
            ranked.append({"score": round(score, 4), "matched_terms": matched, **chunk})
    return sorted(ranked, key=lambda item: (-item["score"], item.get("chunk_id", 0)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chunks")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--context", type=int, default=0, help="Include this many adjacent chunks around hits")
    args = parser.parse_args()
    data = json.loads(Path(args.chunks).read_text(encoding="utf-8-sig"))
    chunks = data.get("chunks", []) if isinstance(data, dict) else []
    hits = rank(chunks, args.query)[:max(1, args.top_k)]
    if args.context and hits:
        by_id = {item.get("chunk_id"): item for item in chunks}
        wanted: set[int] = set()
        for hit in hits:
            chunk_id = int(hit.get("chunk_id", 0))
            wanted.update(range(max(0, chunk_id - args.context), chunk_id + args.context + 1))
        context_chunks = [by_id[index] for index in sorted(wanted) if index in by_id]
    else:
        context_chunks = []
    result = {"query": args.query, "total_chunks": len(chunks), "hit_count": len(hits), "hits": hits, "context_chunks": context_chunks}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if hits else 3


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
