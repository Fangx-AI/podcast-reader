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
EVIDENCE_STOP_TERMS = {
    "这期", "节目", "认为", "看法", "什么", "关系", "如何", "怎么", "怎样",
    "为何", "为什么", "是否", "觉得", "提到", "关于", "他的", "她的", "他们",
}


def terms(value: str) -> list[str]:
    value = value.casefold()
    result = LATIN_TERM.findall(value)
    for run in CJK_RUN.findall(value):
        result.extend(run[index:index + 2] for index in range(max(1, len(run) - 1)))
        if len(run) <= 4:
            result.append(run)
    return list(dict.fromkeys(term for term in result if term))


def nested_segment_ids(value: Any) -> set[int]:
    found: set[int] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "segment_ids" and isinstance(child, list):
                found.update(item for item in child if isinstance(item, int))
            else:
                found.update(nested_segment_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(nested_segment_ids(child))
    return found


def expand_from_evidence(
    query: str, evidence_path: Path | None,
) -> tuple[str, list[dict[str, Any]], dict[int, float], list[dict[str, Any]]]:
    if not evidence_path or not evidence_path.is_file():
        return query, [], {}, []
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return query, [], {}, []
    lowered = query.casefold()
    additions: list[str] = []
    expansions: list[dict[str, Any]] = []
    for item in evidence.get("glossary", []) if isinstance(evidence, dict) else []:
        if not isinstance(item, dict):
            continue
        labels = [str(item.get("source_term") or "").strip(), str(item.get("preferred_term") or "").strip()]
        labels.extend(str(value).strip() for value in item.get("aliases", []) if str(value).strip())
        labels = list(dict.fromkeys(value for value in labels if value))
        matched = [value for value in labels if value.casefold() in lowered]
        if matched:
            added = [value for value in labels if value.casefold() not in lowered and value not in additions]
            additions.extend(added)
            if added:
                expansions.append({"matched": matched, "added": added, "source": "evidence.glossary"})

    query_terms = [term for term in terms(query) if term not in EVIDENCE_STOP_TERMS]
    boosts: dict[int, float] = {}
    evidence_matches: list[dict[str, Any]] = []
    searchable_fields = {
        "claims": ("claim",),
        "actions": ("action", "for_whom"),
        "entities": ("name", "context"),
        "glossary": ("source_term", "preferred_term", "note"),
    }
    for collection, fields in searchable_fields.items():
        for index, item in enumerate(evidence.get(collection, []) if isinstance(evidence, dict) else []):
            if not isinstance(item, dict):
                continue
            searchable = " ".join(str(item.get(field) or "") for field in fields).casefold()
            matched_terms = [term for term in query_terms if term in searchable]
            segment_ids = nested_segment_ids(item)
            if not matched_terms or not segment_ids:
                continue
            boost = min(14.0, 4.0 + 2.0 * len(matched_terms))
            for segment_id in segment_ids:
                boosts[segment_id] = max(boosts.get(segment_id, 0.0), boost)
            evidence_matches.append({
                "collection": collection,
                "index": index,
                "matched_terms": matched_terms,
                "segment_ids": sorted(segment_ids),
                "boost": boost,
            })
    expanded = " ".join([query, *additions]).strip()
    return expanded, expansions, boosts, evidence_matches


def rank(chunks: list[dict[str, Any]], query: str, segment_boosts: dict[int, float] | None = None) -> list[dict[str, Any]]:
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
        chunk_segment_ids = [item for item in chunk.get("segment_ids", []) if isinstance(item, int)]
        evidence_boost = max((segment_boosts or {}).get(item, 0.0) for item in chunk_segment_ids) if chunk_segment_ids else 0.0
        score += evidence_boost
        if score:
            ranked.append({"score": round(score, 4), "matched_terms": matched, "evidence_boost": evidence_boost, **chunk})
    return sorted(ranked, key=lambda item: (-item["score"], item.get("chunk_id", 0)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chunks")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--context", type=int, default=0, help="Include this many adjacent chunks around hits")
    parser.add_argument("--evidence", help="Optional evidence.json for cross-language glossary expansion; defaults beside chunks.json")
    parser.add_argument("--no-expand", action="store_true", help="Disable automatic glossary expansion")
    args = parser.parse_args()
    chunks_path = Path(args.chunks).expanduser().resolve()
    data = json.loads(chunks_path.read_text(encoding="utf-8-sig"))
    chunks = data.get("chunks", []) if isinstance(data, dict) else []
    evidence_path = Path(args.evidence).expanduser().resolve() if args.evidence else chunks_path.with_name("evidence.json")
    expanded_query, expansions, segment_boosts, evidence_matches = (
        (args.query, [], {}, []) if args.no_expand else expand_from_evidence(args.query, evidence_path)
    )
    hits = rank(chunks, expanded_query, segment_boosts)[:max(1, args.top_k)]
    if args.context and hits:
        by_id = {item.get("chunk_id"): item for item in chunks}
        wanted: set[int] = set()
        for hit in hits:
            chunk_id = int(hit.get("chunk_id", 0))
            wanted.update(range(max(0, chunk_id - args.context), chunk_id + args.context + 1))
        context_chunks = [by_id[index] for index in sorted(wanted) if index in by_id]
    else:
        context_chunks = []
    result = {
        "query": args.query,
        "expanded_query": expanded_query,
        "expansions": expansions,
        "evidence_matches": evidence_matches,
        "evidence_source": str(evidence_path) if expansions or evidence_matches else None,
        "total_chunks": len(chunks),
        "hit_count": len(hits),
        "hits": hits,
        "context_chunks": context_chunks,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if hits else 3


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
