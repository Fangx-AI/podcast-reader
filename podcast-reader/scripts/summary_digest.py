#!/usr/bin/env python3
"""Validate and render a concise, source-grounded Podcast Reader digest."""

from __future__ import annotations

import argparse
import html
import math
import re
from typing import Any
from urllib.parse import quote, urlsplit

from evidence_validator import validate_reference


TEXT_BUDGET = 12_000
PLACEHOLDER = re.compile(
    r"\b(?:TODO|TBD|FIXME)\b|待补充|待填写|待生成|\{\{[^{}]+\}\}|"
    r"<(?:insert|replace|填写|填入)[^>]*>",
    re.IGNORECASE,
)
DIGEST_FIELDS = {"headline", "takeaway", "evidence", "participants", "quick_takes", "insights", "open_questions"}
INSIGHT_KINDS = {
    "decision": "决策判断", "counterintuitive": "反直觉观点", "data": "关键数据",
    "method": "具体方法", "pitfall": "需要避开的坑", "insight": "重要洞察",
}
ENGLISH_INSIGHT_KINDS = {
    "decision": "Decision", "counterintuitive": "Counterintuitive insight", "data": "Key data",
    "method": "Method", "pitfall": "Pitfall", "insight": "Insight",
}


def _seconds(value: Any) -> float | None:
    """Parse real timestamps without accepting booleans, NaN or invalid clocks."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            parsed = float(value)
        except OverflowError:
            return None
        return parsed if math.isfinite(parsed) else None
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"(?:(\d+):)?(\d+):(\d{1,2}(?:[.,]\d+)?)", value.strip())
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    try:
        minute_value, second_value = int(minutes), float(seconds.replace(",", "."))
        result = int(hours or 0) * 3600 + minute_value * 60 + second_value
    except (OverflowError, ValueError):
        return None
    if second_value >= 60 or (hours is not None and minute_value >= 60):
        return None
    return float(result) if math.isfinite(result) else None


def _segments(transcript: Any) -> dict[int, dict[str, Any]]:
    if not isinstance(transcript, dict) or not isinstance(transcript.get("segments"), list):
        return {}
    return {
        segment["segment_id"]: segment
        for segment in transcript["segments"]
        if isinstance(segment, dict)
        and type(segment.get("segment_id")) is int
        and segment["segment_id"] >= 0
    }


def _bounds(segment: dict[str, Any]) -> tuple[float | None, float | None]:
    start = _seconds(segment.get("start_seconds", segment.get("start")))
    end = _seconds(segment.get("end_seconds", segment.get("end")))
    return start, end


def _duration(segments: dict[int, dict[str, Any]]) -> float:
    return max(
        (value for segment in segments.values() for value in _bounds(segment) if value is not None),
        default=0.0,
    )


def _reference(reference: Any, segments: dict[int, dict[str, Any]], duration: float,
               label: str, errors: list[str]) -> set[int]:
    if not isinstance(reference, dict):
        errors.append(f"{label}: evidence reference must be an object")
        return set()
    ids = reference.get("segment_ids")
    if not isinstance(ids, list) or not ids or any(type(item) is not int or item < 0 for item in ids):
        errors.append(f"{label}: segment_ids must be a non-empty list of nonnegative integers (not booleans)")
        return set()
    if len(ids) != len(set(ids)):
        errors.append(f"{label}: segment_ids must not contain duplicates")
    start, end = reference.get("start"), reference.get("end")
    parsed_start, parsed_end = _seconds(start), _seconds(end)
    timed = start is not None or end is not None
    if timed and (parsed_start is None or parsed_end is None):
        errors.append(f"{label}: timestamps must both be finite numbers or valid clock strings")
        # Still check segment membership, without passing malformed clocks upstream.
        return validate_reference({"segment_ids": ids}, segments, duration, label, errors)
    # Reuse the shared membership and range validator with canonical numeric times.
    canonical = {"segment_ids": ids, "start": parsed_start, "end": parsed_end}
    canonical_segments = {
        segment_id: {"start_seconds": _bounds(segments[segment_id])[0], "end_seconds": _bounds(segments[segment_id])[1]}
        for segment_id in ids if segment_id in segments
    }
    found = validate_reference(canonical, canonical_segments, duration, label, errors)
    if timed:
        bounds = [_bounds(segments[item]) for item in ids if item in segments]
        if any(left is None or right is None for left, right in bounds):
            errors.append(f"{label}: cannot attach timestamps to untimed transcript segments")
        elif bounds:
            minimum = min(left for left, _ in bounds)
            maximum = max(right for _, right in bounds)
            if parsed_start < minimum - 2 or parsed_end > maximum + 2:
                errors.append(f"{label}: timestamps extend beyond referenced segments")
            if any(parsed_end < left - 2 or parsed_start > right + 2 for left, right in bounds):
                errors.append(f"{label}: timestamps must overlap every referenced segment")
    return found


def validate_digest(evidence: Any, transcript: Any, required: bool = False) -> dict[str, Any]:
    """Check the optional digest; require it when finalizing a new summary bundle.

    This supplements validate_evidence: quote exactness and legacy evidence
    collections remain the shared validator's responsibility.
    """
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, Any] = {"digest_present": False, "text_characters": 0, "cited_segments": 0}

    def result() -> dict[str, Any]:
        return {"valid": not errors, "errors": errors, "warnings": warnings, "metrics": metrics}

    if not isinstance(evidence, dict):
        errors.append("evidence root must be an object")
        return result()
    if "digest" not in evidence:
        if required:
            errors.append("digest is required for a concise summary")
        return result()
    digest = evidence["digest"]
    metrics["digest_present"] = True
    if not isinstance(digest, dict):
        errors.append("digest must be an object")
        return result()
    segments = _segments(transcript)
    duration = _duration(segments)
    if not segments:
        errors.append("transcript contains no addressable segments")
    cited: set[int] = set()
    text_parts: list[str] = []

    def fields(item: dict[str, Any], allowed: set[str], label: str) -> None:
        unexpected = sorted(set(item) - allowed)
        if unexpected:
            errors.append(f"{label}: unknown fields {unexpected}")

    def text(value: Any, label: str, maximum: int, optional: bool = False) -> None:
        if optional and value is None:
            return
        if not isinstance(value, str) or (not optional and not value.strip()):
            errors.append(f"{label}: must be a {'non-empty ' if not optional else ''}string")
            return
        text_parts.append(value)
        if len(value) > maximum:
            errors.append(f"{label}: exceeds {maximum} characters")
        if PLACEHOLDER.search(value):
            errors.append(f"{label}: contains an unfinished template placeholder")

    def items(value: Any, label: str, maximum: int, minimum: int = 0,
              nullable: bool = False) -> list[Any]:
        if nullable and value is None:
            return []
        if not isinstance(value, list):
            errors.append(f"{label}: must be a list")
            return []
        if not minimum <= len(value) <= maximum:
            errors.append(f"{label}: must contain {minimum}–{maximum} items")
        return value

    def refs(value: Any, label: str) -> None:
        for index, reference in enumerate(items(value, label, 12, minimum=1)):
            cited.update(_reference(reference, segments, duration, f"{label}[{index}]", errors))

    episode = evidence.get("episode")
    if episode is not None and not isinstance(episode, dict):
        errors.append("episode must be an object")
    elif isinstance(episode, dict):
        for field, maximum in (("title", 300), ("show", 160), ("published", 80)):
            text(episode.get(field), f"episode.{field}", maximum, optional=True)
    fields(digest, DIGEST_FIELDS, "digest")
    text(digest.get("headline"), "digest.headline", 120)
    text(digest.get("takeaway"), "digest.takeaway", 400)
    refs(digest.get("evidence"), "digest.evidence")
    for index, item in enumerate(items(digest.get("participants"), "digest.participants", 8, nullable=True)):
        label = f"digest.participants[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: must be an object")
            continue
        fields(item, {"name", "role", "description"}, label)
        text(item.get("name"), f"{label}.name", 100)
        text(item.get("role"), f"{label}.role", 100, optional=True)
        text(item.get("description"), f"{label}.description", 300, optional=True)
    for index, item in enumerate(items(digest.get("quick_takes"), "digest.quick_takes", 6, minimum=1)):
        label = f"digest.quick_takes[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: must be an object")
            continue
        fields(item, {"question", "answer", "evidence"}, label)
        text(item.get("question"), f"{label}.question", 160)
        text(item.get("answer"), f"{label}.answer", 500)
        refs(item.get("evidence"), f"{label}.evidence")
    for index, item in enumerate(items(digest.get("insights"), "digest.insights", 7, minimum=1)):
        label = f"digest.insights[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: must be an object")
            continue
        fields(item, {"title", "summary", "bullets", "evidence", "kind"}, label)
        if item.get("kind") is not None and (
            not isinstance(item["kind"], str) or item["kind"] not in INSIGHT_KINDS
        ):
            errors.append(f"{label}.kind: must be one of {sorted(INSIGHT_KINDS)}")
        text(item.get("title"), f"{label}.title", 160)
        text(item.get("summary"), f"{label}.summary", 700)
        for bullet_index, bullet in enumerate(items(item.get("bullets"), f"{label}.bullets", 4, nullable=True)):
            text(bullet, f"{label}.bullets[{bullet_index}]", 300)
        refs(item.get("evidence"), f"{label}.evidence")
    for index, item in enumerate(items(digest.get("open_questions"), "digest.open_questions", 5, nullable=True)):
        text(item, f"digest.open_questions[{index}]", 300)

    for index, item in enumerate(items(evidence.get("quotes", []), "quotes", 3)):
        label = f"quotes[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: must be an object")
            continue
        text(item.get("text"), f"{label}.text", 500)
        text(item.get("speaker"), f"{label}.speaker", 100, optional=True)
        cited.update(_reference(item, segments, duration, label, errors))
    for index, item in enumerate(items(evidence.get("actions", []), "actions", 5)):
        label = f"actions[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: must be an object")
            continue
        text(item.get("action"), f"{label}.action", 500)
        text(item.get("for_whom"), f"{label}.for_whom", 160, optional=True)
        for field in ("prerequisites", "risks"):
            for position, value in enumerate(items(item.get(field), f"{label}.{field}", 4, nullable=True)):
                text(value, f"{label}.{field}[{position}]", 300)
        refs(item.get("evidence"), f"{label}.evidence")
    for index, item in enumerate(items(evidence.get("chapters", []), "chapters", 20)):
        label = f"chapters[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label}: must be an object")
            continue
        text(item.get("title"), f"{label}.title", 160)
        text(item.get("summary"), f"{label}.summary", 400, optional=True)
        start, end = _seconds(item.get("start")), _seconds(item.get("end"))
        if start is None or end is None or start < 0 or end < start or end > duration + 2:
            errors.append(f"{label}: requires a finite timestamp range within the transcript")
        if not any(_bounds(segment)[0] is not None for segment in segments.values()):
            errors.append(f"{label}: cannot create timed chapters for an untimed transcript")
    for index, item in enumerate(items(evidence.get("limitations", []), "limitations", 12)):
        text(item, f"limitations[{index}]", 500)
    total = sum(len(value) for value in text_parts)
    if total > TEXT_BUDGET:
        errors.append(f"digest: rendered text exceeds the {TEXT_BUDGET}-character concise-summary budget")
    metrics.update({
        "text_characters": total,
        "cited_segments": len(cited),
        "quick_takes": len(digest.get("quick_takes", [])) if isinstance(digest.get("quick_takes"), list) else 0,
        "insights": len(digest.get("insights", [])) if isinstance(digest.get("insights"), list) else 0,
    })
    return result()


def _escape(value: Any) -> str:
    """Keep supplied text literal in Markdown and in HTML-capable renderers."""
    normalized = re.sub(r"\s+", " ", str(value or "")).strip()
    escaped = html.escape(normalized, quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+.!|~-])", r"\\\1", escaped)


def _stamp(value: float) -> str:
    whole = int(value)
    return f"{whole // 3600:02d}:{whole % 3600 // 60:02d}:{whole % 60:02d}"


def _citation(reference: dict[str, Any], segments: dict[int, dict[str, Any]], english: bool = False) -> str:
    start, end = _seconds(reference.get("start")), _seconds(reference.get("end"))
    ids = reference.get("segment_ids") or []
    if start is None or end is None:
        bounds = [_bounds(segments[item]) for item in ids if item in segments]
        if bounds and all(left is not None and right is not None for left, right in bounds):
            start = min(left for left, _ in bounds)
            end = max(right for _, right in bounds)
    if start is not None and end is not None:
        return f"[{_stamp(start)}–{_stamp(end)}]"
    return (", " if english else "、").join(
        f"{'Text segment' if english else '文本段'} #{item}" for item in ids
    )


def _citations(references: list[dict[str, Any]], segments: dict[int, dict[str, Any]], english: bool = False) -> str:
    return " ".join(dict.fromkeys(_citation(reference, segments, english) for reference in references))


def _source_link(value: Any, english: bool = False) -> str:
    if not isinstance(value, str) or any(ord(character) < 32 for character in value):
        return ""
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"https", "http"} or not parsed.hostname:
            return ""
    except ValueError:
        return ""
    encoded = quote(value, safe=":/?#@!$&'+,;=%~-._")
    return f"[{'Listen to the episode' if english else '收听原节目'}](<{encoded}>)"


def _local_source(value: Any, english: bool) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value) and not re.match(r"^[A-Za-z]:[\\/]", value):
        return ""
    name = value.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    is_text = name.lower().endswith((".txt", ".md", ".srt", ".vtt", ".json", ".csv", ".ass", ".ttml"))
    label = ("Local text" if is_text else "Local file") if english else ("本地文本" if is_text else "本地文件")
    return f"{label} · {_escape(name)}" if name else ""


def render_markdown(evidence: dict[str, Any], bundle: dict[str, Any],
                    transcript: dict[str, Any]) -> str:
    """Render a validated digest without introducing unsupported conclusions."""
    validation = validate_digest(evidence, transcript, required=True)
    if not validation["valid"]:
        raise ValueError("invalid digest: " + "; ".join(validation["errors"]))
    digest = evidence["digest"]
    segments = _segments(transcript)
    language = str(bundle.get("output_language") or "zh-CN").strip().lower()
    english = language in {"en", "english"} or language.startswith("en-")
    def label(zh: str, en: str) -> str:
        return en if english else zh

    episode = evidence.get("episode") if isinstance(evidence.get("episode"), dict) else {}
    resolution = bundle.get("resolution") if isinstance(bundle.get("resolution"), dict) else {}
    title = episode.get("title") or resolution.get("title")
    metadata = [_escape(value) for value in (episode.get("show"), title, episode.get("published")) if value]
    source = _source_link(episode.get("source_url"), english) or _source_link(bundle.get("source_input"), english)
    if source:
        metadata.append(source)
    else:
        local_source = _local_source(bundle.get("source_input"), english)
        if local_source:
            metadata.append(local_source)
    if not metadata:
        metadata.append(label("转写材料", "Transcript"))
    lines = [f"# {_escape(digest['headline'])}", ""]
    lines.extend([label("## 一句话总结", "## One-sentence takeaway"), "", _escape(digest["takeaway"]), "",
                  _citations(digest["evidence"], segments, english), ""])
    lines.extend([label("## 关键问题 · 直接看答案", "## Key questions · Direct answers"), ""])
    for item in digest["quick_takes"]:
        lines.extend([f"### {_escape(item['question'])}", "", _escape(item["answer"]), "",
                      _citations(item["evidence"], segments, english), ""])
    lines.extend([label("## 高价值信息", "## High-value insights"), ""])
    for number, item in enumerate(digest["insights"], 1):
        kind_labels = ENGLISH_INSIGHT_KINDS if english else INSIGHT_KINDS
        kind = f" · {kind_labels[item['kind']]}" if item.get("kind") else ""
        lines.extend([f"### {number}. {_escape(item['title'])}{kind}", "", _escape(item["summary"]), ""])
        if item.get("bullets"):
            lines.extend(f"- {_escape(bullet)}" for bullet in item["bullets"])
            lines.append("")
        lines.extend([_citations(item["evidence"], segments, english), ""])
    if evidence.get("quotes"):
        lines.extend([label("## 值得记住的原话", "## Memorable quotes"), ""])
        for item in evidence["quotes"]:
            attribution = f" — {_escape(item['speaker'])}" if item.get("speaker") else ""
            lines.extend([f"> {_escape(item['text'])}", "", f"{attribution.strip()} {_citation(item, segments, english)}".strip(), ""])
    if evidence.get("actions"):
        lines.extend([label("## 可以怎么做", "## What you can do"), ""])
        for item in evidence["actions"]:
            audience = label(f"（适用：{_escape(item.get('for_whom'))}）", f" (For: {_escape(item.get('for_whom'))})") if item.get("for_whom") else ""
            lines.append(f"- {_escape(item['action'])}{audience} {_citations(item['evidence'], segments, english)}")
            for field, field_label in (("prerequisites", label("前提：", "Prerequisites: ")), ("risks", label("风险：", "Risks: "))):
                if item.get(field):
                    lines.append(f"  {field_label}" + label("；", "; ").join(_escape(value) for value in item[field]))
        lines.append("")
    if digest.get("open_questions"):
        lines.extend([label("## 仍未解决的问题", "## Open questions"), ""])
        lines.extend(f"- {_escape(item)}" for item in digest["open_questions"])
        lines.append("")
    participants = digest.get("participants") or []
    if participants:
        lines.extend([label("## 对谈双方" if len(participants) == 2 else "## 本期人物", "## Participants"), ""])
        for person in participants:
            detail = " · ".join(_escape(person.get(field)) for field in ("role", "description") if person.get(field))
            lines.append(f"- **{_escape(person['name'])}**" + (label("：", ": ") + detail if detail else ""))
        lines.append("")
    if metadata:
        lines.extend([label("来源：", "Source: ") + " · ".join(metadata), ""])
    if evidence.get("limitations"):
        lines.extend([label("## 说明与限制", "## Notes and limitations"), ""])
        lines.extend(f"- {_escape(item)}" for item in evidence["limitations"])
        lines.append("")
    if evidence.get("chapters"):
        lines.extend([label("## 回听章节", "## Listening chapters"), ""])
        for item in evidence["chapters"]:
            detail = label("：", ": ") + _escape(item["summary"]) if item.get("summary") else ""
            lines.append(f"- {_citation(item, segments, english)} **{_escape(item['title'])}**{detail}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print("Podcast Reader digest library; use finalize_bundle.py to render summary.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
