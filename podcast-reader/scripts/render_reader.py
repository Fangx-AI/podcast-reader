#!/usr/bin/env python3
"""Render a compact, evidence-linked podcast summary as a standalone HTML page."""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path
import re
import sys
from typing import Any
import urllib.parse

from runtime_utils import atomic_write_text
from reader_ui import STYLE, TOOLBAR_SCRIPT, TRANSCRIPT_SCRIPT
from summary_digest import render_markdown


def safe_source_url(value: Any) -> str | None:
    """Allow ordinary HTTP(S) links only; never embed executable or local URLs."""
    if not isinstance(value, str) or re.search(r"[\s\\\x00-\x1f\x7f]", value):
        return None
    try:
        parsed = urllib.parse.urlsplit(value)
        if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
            return None
        if parsed.username or parsed.password:
            return None
        parsed.port  # Validate malformed ports without rewriting the source.
    except ValueError:
        return None
    return value


def timestamp_url(source_url: str | None, value: float) -> str | None:
    """Return a real seek URL on supported platforms, otherwise no seek link."""
    source_url = safe_source_url(source_url)
    seconds = seconds_value(value)
    if not source_url or seconds is None:
        return None
    parsed = urllib.parse.urlsplit(source_url)
    host = (parsed.hostname or "").casefold()
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    seconds = int(seconds)
    if host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com"):
        query = [(key, item) for key, item in query if key not in {"t", "start"}] + [("t", f"{seconds}s")]
    elif host == "b23.tv" or host == "bilibili.com" or host.endswith(".bilibili.com"):
        query = [(key, item) for key, item in query if key != "t"] + [("t", str(seconds))]
    else:
        return None
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), ""))


def seconds_value(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str) and ":" in value:
        parts = value.split(":")
        if len(parts) not in {2, 3}:
            return None
        try:
            numbers = [float(part) for part in parts]
        except ValueError:
            return None
        if any(not math.isfinite(part) or part < 0 for part in numbers) or any(part >= 60 for part in numbers[1:]):
            return None
        total = sum(part * 60 ** power for power, part in enumerate(reversed(numbers)))
        return total if math.isfinite(total) else None
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def stamp(value: float) -> str:
    whole = int(value)
    return f"{whole // 3600:02d}:{whole // 60 % 60:02d}:{whole % 60:02d}"


def esc(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def records(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def strings(value: Any) -> list[str]:
    return [item.strip() for item in value if isinstance(item, str) and item.strip()] if isinstance(value, list) else []


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


LABELS = {
    "zh": {
        "language": "zh-CN", "brand": "播客省流版", "takeaway": "一句话看懂",
        "participants": "对谈双方", "quick": "关键问题 · 直接看答案", "insights": "高价值信息",
        "quotes": "值得记住的原话", "actions": "可以带走的行动", "limitations": "阅读提示",
        "open_questions": "仍未解决的问题", "details": "展开章节与逐字稿", "chapters": "节目章节",
        "details_chapters": "展开节目章节", "transcript": "原始逐字稿",
        "search": "搜索逐字稿", "placeholder": "输入人物、概念或原话", "source": "收听原节目",
        "segment": "原文段落", "evidence": "查看依据", "untimed": "时间未标注",
        "skip": "跳到省流总结", "footer": "Podcast Reader · 把时间留给值得听的部分",
        "pending": "省流总结尚未生成。可以查看原文了解节目内容。",
        "prerequisites": "适用前提", "risks": "注意事项", "claim": "节目观点", "minutes": "分钟",
        "count_all": "共 {n} 段", "count_match": "找到 {n} 段", "evidence_missing": "未提供原文定位",
        "decision": "决策依据", "counterintuitive": "反直觉", "data": "关键数据",
        "method": "方法步骤", "pitfall": "避坑提醒", "insight": "关键洞察",
        "copy": "复制摘要", "save": "保存摘要", "copied": "摘要已复制，可直接粘贴分享。",
        "copy_manual": "无法自动复制。请复制下面已选中的文字。",
        "copy_help": "使用 Ctrl+C（Mac 为 ⌘C），或长按选中文字进行复制。",
        "copy_close": "收起", "copy_text": "摘要全文", "saved": "已开始保存 Markdown 摘要。",
        "save_failed": "无法自动保存，请复制下方摘要后自行保存。",
        "nav": "摘要目录", "nav_quick": "关键问题", "nav_insights": "高价值信息",
        "nav_quotes": "精选原话", "nav_open_questions": "未解问题", "nav_source": "查看原文",
        "clear": "清除", "reset": "清除搜索", "empty_title": "没有找到匹配内容",
        "empty_help": "试试更短的关键词，或清除搜索查看完整逐字稿。",
        "return": "返回刚才的摘要", "top": "回到顶部", "view_text": "查看原文",
        "view_episode": "回听此处", "reading": "约 {n} 分钟读完", "duration": "原节目 {n} 分钟",
        "questions_count": "{n} 个关键问题", "insights_count": "{n} 条高价值信息",
        "reading_basis": "按摘要正文约 400 中文字或 200 英文词／分钟估算，不含逐字稿。",
        "pending_title": "总结尚未生成", "stale": "这份摘要尚未完成校验，内容可能仍在更新。",
        "reference": "依据",
        "core_question": "本期核心问题", "question_index": "本期关键问题",
        "question_index_hint": "选择一个问题，往下看", "question_details": "逐题看：回答与未解之处",
        "why_it_matters": "为什么值得问", "episode_answer": "节目回答", "gap": "仍缺什么",
        "answered": "节目有回答", "partial": "部分回答", "unanswered": "未解答",
        "explicit": "节目中提出", "synthesized": "由内容提炼",
    },
    "en": {
        "language": "en", "brand": "PODCAST, CONDENSED", "takeaway": "The takeaway",
        "participants": "The voices", "quick": "Key questions · Direct answers", "insights": "High-value insights",
        "quotes": "In their own words", "actions": "Ideas to act on", "limitations": "Reading notes",
        "open_questions": "Questions left open", "details": "Explore chapters & transcript", "chapters": "Episode chapters",
        "details_chapters": "Explore episode chapters", "transcript": "Original transcript",
        "search": "Search the transcript", "placeholder": "Search a person, idea, or quote", "source": "Listen to the episode",
        "segment": "Transcript segment", "evidence": "View evidence", "untimed": "Time not available",
        "skip": "Skip to the summary", "footer": "Podcast Reader · Make time for what is worth hearing",
        "pending": "The summary has not been generated yet. Refer to the original episode for its content.",
        "prerequisites": "Prerequisites", "risks": "Considerations", "claim": "Episode insight", "minutes": "min",
        "count_all": "{n} segments", "count_match": "{n} matches", "evidence_missing": "No source location supplied",
        "decision": "Decision basis", "counterintuitive": "Counterintuitive", "data": "Key data",
        "method": "Practical method", "pitfall": "Pitfall", "insight": "Key insight",
        "copy": "Copy summary", "save": "Save summary", "copied": "Summary copied. Ready to paste and share.",
        "copy_manual": "Automatic copying is unavailable. Copy the selected text below.",
        "copy_help": "Press Ctrl+C (⌘C on Mac), or touch and hold the selected text to copy.",
        "copy_close": "Close", "copy_text": "Full summary", "saved": "Markdown summary download started.",
        "save_failed": "Automatic saving is unavailable. Copy the summary below and save it.",
        "nav": "Summary sections", "nav_quick": "Key questions", "nav_insights": "Insights",
        "nav_quotes": "Quotes", "nav_open_questions": "Open questions", "nav_source": "Source",
        "clear": "Clear", "reset": "Clear search", "empty_title": "No matching passages",
        "empty_help": "Try a shorter keyword, or clear the search to see the full transcript.",
        "return": "Back to the summary", "top": "Back to top", "view_text": "View source",
        "view_episode": "Listen here", "reading": "About {n} min to read", "duration": "Original episode · {n} min",
        "questions_count": "{n} key questions", "insights_count": "{n} insights",
        "reading_basis": "Estimated at 400 Chinese characters or 200 English words per minute; transcript excluded.",
        "pending_title": "Summary not yet generated", "stale": "This summary has not finished validation and may still be updated.",
        "reference": "Source",
        "core_question": "The episode's central question", "question_index": "Key questions",
        "question_index_hint": "Choose a question to explore", "question_details": "The answers — and what is still missing",
        "why_it_matters": "Why ask this", "episode_answer": "The episode's answer", "gap": "What is still missing",
        "answered": "Answered in the episode", "partial": "Partially answered", "unanswered": "Unanswered",
        "explicit": "Raised in the episode", "synthesized": "Drawn from the discussion",
    },
}


def markdown_summary(evidence: dict[str, Any], bundle: dict[str, Any], transcript: dict[str, Any],
                     title: str, takeaway: str, labels: dict[str, str]) -> str:
    """Embed the canonical summary when valid; keep legacy exports concise."""
    try:
        return render_markdown(evidence, {**bundle, "output_language": labels["language"]}, transcript)
    except (ValueError, TypeError, KeyError):
        pass
    def literal(value: Any) -> str:
        value = html.escape(str(value or ""), quote=False)
        return re.sub(r"([\\`*_{}\[\]()#+.!|~-])", r"\\\1", value)
    digest = evidence.get("digest") if isinstance(evidence.get("digest"), dict) else {}
    lines = [f"# {literal(title)}", "", f"## {labels['takeaway']}", "", literal(takeaway), ""]
    for item in records(digest.get("quick_takes")):
        if item.get("question"):
            lines.extend([f"### {literal(item['question'])}", ""])
            for field in ("answer_status", "question_origin"):
                value = item.get(field)
                if isinstance(value, str) and value in {"answered", "partial", "unanswered", "explicit", "synthesized"}:
                    lines.extend([labels[value], ""])
            for field, label in (("why_it_matters", "why_it_matters"), ("answer", "episode_answer"), ("gap", "gap")):
                if item.get(field):
                    lines.extend([f"**{labels[label]}**", "", literal(item[field]), ""])
    insights = records(digest.get("insights")) or [
        {"title": item.get("claim"), "summary": item.get("speaker")}
        for item in records(evidence.get("claims")) if item.get("claim")
    ]
    for item in insights:
        if item.get("title") or item.get("summary"):
            lines.extend([f"### {literal(item.get('title') or labels['claim'])}", "", literal(item.get("summary")), ""])
            lines.extend(f"- {literal(value)}" for value in strings(item.get("bullets")))
            lines.append("")
    for item in records(evidence.get("quotes"))[:3]:
        if item.get("text"):
            lines.extend([f"> {literal(item['text'])}", "", literal(item.get("speaker")), ""])
    for item in records(evidence.get("actions")):
        if item.get("action"):
            lines.extend([f"- {literal(item['action'])}", ""])
    for key, values in (("open_questions", digest.get("open_questions")), ("limitations", evidence.get("limitations"))):
        if strings(values):
            lines.extend([f"## {labels[key]}", ""])
            lines.extend(f"- {literal(value)}" for value in strings(values))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def reading_minutes(content: str) -> int:
    """Estimate only visible summary text, treating CJK glyphs as characters."""
    text = html.unescape(re.sub(r"<[^>]*>", " ", content))
    cjk = len(re.findall(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7af]", text))
    words = len(re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+(?:['’-][A-Za-zÀ-ÖØ-öø-ÿ]+)*", text))
    return max(1, math.ceil(cjk / 400 + words / 200))



def render(episode_dir: Path, output: Path, *, include_transcript: bool = True,
           finalized: bool | None = None) -> dict[str, Any]:
    episode_dir = episode_dir.expanduser().resolve()
    transcript = load(episode_dir / "transcript.json")
    bundle = load(episode_dir / "bundle.json")
    evidence_path = episode_dir / "evidence.json"
    evidence = load(evidence_path) if evidence_path.is_file() else {}
    handoff_path = episode_dir / "analysis-handoff.json"
    handoff = load(handoff_path) if handoff_path.is_file() else {}
    request = bundle.get("request") if isinstance(bundle.get("request"), dict) else {}
    language = str(bundle.get("output_language") or request.get("output_language") or handoff.get("output_language") or evidence.get("output_language") or "").strip().casefold()
    english = language in {"en", "english"} or language.startswith(("en-", "en_"))
    labels = dict(LABELS["en" if english else "zh"])
    episode = evidence.get("episode") if isinstance(evidence.get("episode"), dict) else {}
    resolution = bundle.get("resolution") if isinstance(bundle.get("resolution"), dict) else {}
    digest = evidence.get("digest") if isinstance(evidence.get("digest"), dict) else {}
    source_url = next((url for value in (episode.get("source_url"), bundle.get("source_input"), resolution.get("webpage_url"), resolution.get("url")) if (url := safe_source_url(value))), None)
    original_title = str(episode.get("title") or resolution.get("title") or episode_dir.name)
    core_question = digest.get("core_question")
    core_question = core_question.strip() if isinstance(core_question, str) else ""
    title = str(core_question or digest.get("headline") or original_title)
    takeaway = str(digest.get("takeaway") or evidence.get("summary") or labels["pending"])
    segments = records(transcript.get("segments"))
    segment_map = {str(item.get("segment_id", index)): item for index, item in enumerate(segments, 1)}
    timestamp_link_count = 0
    reference_count = 0

    def references(items: Any, *, mark_missing: bool = False, compact: bool = False) -> str:
        nonlocal timestamp_link_count, reference_count
        links = []
        seen = set()
        for item in records(items):
            ids = [str(value) for value in item.get("segment_ids", []) if str(value) in segment_map] if isinstance(item.get("segment_ids"), list) else []
            linked_segments = [segment_map[value] for value in ids]
            anchor_id = ids[0] if ids else None
            start = seconds_value(item.get("start"))
            end = seconds_value(item.get("end"))
            if linked_segments:
                bounds = []
                for segment in linked_segments:
                    left = seconds_value(segment.get("start_seconds"))
                    right = seconds_value(segment.get("end_seconds"))
                    bounds.append((
                        left if left is not None else seconds_value(segment.get("start")),
                        right if right is not None else seconds_value(segment.get("end")),
                    ))
                if all(left is not None and right is not None for left, right in bounds):
                    anchor_id = ids[min(range(len(bounds)), key=lambda index: bounds[index][0])]
                    if start is None:
                        start = min(left for left, _ in bounds)
                    if end is None:
                        end = max(right for _, right in bounds)
            label = stamp(start) if start is not None else f'{labels["segment"]} {", ".join(ids)}' if ids else labels["untimed"]
            if start is not None and end is not None and end > start:
                label += "–" + stamp(end)
            link = timestamp_url(source_url, start) if start is not None else None
            reference_key = (label, link, anchor_id)
            if reference_key in seen:
                continue
            seen.add(reference_key)
            reference_count += 1
            reference_id = f"reference-{reference_count}"
            time_html = f'<span class="reference-time">{esc(label)}</span>'
            compact_html = f'<span class="compact-reference">{esc(labels["reference"])} {len(links) + 1} ↗</span>' if compact else ""
            if link:
                description = labels["view_episode"] + ": " + label
                entry = f'<a id="{reference_id}" href="{esc(link)}" target="_blank" rel="noopener noreferrer" title="{esc(description)}" aria-label="{esc(description)}">{time_html}<span class="evidence-action">{esc(labels["view_episode"])} ↗</span>{compact_html}</a>'
                timestamp_link_count += 1
            elif ids and include_transcript:
                description = labels["view_text"] + ": " + label
                entry = f'<a id="{reference_id}" class="segment-reference" href="#segment-{esc(anchor_id)}" title="{esc(description)}" aria-label="{esc(description)}">{time_html}<span class="evidence-action">{esc(labels["view_text"])} ↗</span>{compact_html}</a>'
            else:
                plain_compact = f'<span class="compact-reference">{esc(labels["reference"])} {len(links) + 1}</span>' if compact else ""
                entry = f'<span title="{esc(label)}" aria-label="{esc(label)}">{time_html}{plain_compact}</span>'
            links.append(entry)
        if not links and mark_missing:
            links.append(f'<span>{esc(labels["evidence_missing"])}</span>')
        return f'<div class="evidence{" compact-evidence" if compact else ""}">{"".join(links)}</div>' if links else ""

    def section(key: str, content: str, class_name: str = "", count: int = 0) -> str:
        if not content:
            return ""
        counter = f'<span class="section-count" aria-hidden="true">{count:02d}</span>' if count else ""
        return f'<section id="{key}" class="{esc(class_name)}" aria-labelledby="{key}-title"><div class="section-heading"><h2 id="{key}-title">{esc(labels[key])}</h2>{counter}</div>{content}</section>'

    participants = []
    for item in records(digest.get("participants")):
        if not item.get("name"):
            continue
        role = f'<div class="role">{esc(item["role"])}</div>' if item.get("role") else ""
        description = f'<p>{esc(item["description"])}</p>' if item.get("description") else ""
        participants.append(f'<article class="card participant"><h3>{esc(item["name"])}</h3>{role}{description}</article>')
    if participants and len(participants) != 2 and not english:
        labels["participants"] = "本期人物"

    quick_rows = []
    question_links = []
    for item in records(digest.get("quick_takes")):
        if not item.get("question"):
            continue
        number = len(quick_rows) + 1
        answer_status, question_origin = item.get("answer_status"), item.get("question_origin")
        status_html = f'<span class="question-status" data-answer-status="{answer_status}">{esc(labels[answer_status])}</span>' if isinstance(answer_status, str) and answer_status in {"answered", "partial", "unanswered"} else ""
        origin_html = f'<span class="question-origin" data-question-origin="{question_origin}">{esc(labels[question_origin])}</span>' if isinstance(question_origin, str) and question_origin in {"explicit", "synthesized"} else ""
        question_meta = f'<div class="question-meta">{status_html}{origin_html}</div>' if status_html or origin_html else ""
        why_html = f'<p class="question-why"><span class="field-label">{esc(labels["why_it_matters"])}</span>{esc(item["why_it_matters"])}</p>' if item.get("why_it_matters") else ""
        answer_html = f'<div class="question-answer"><span class="field-label">{esc(labels["episode_answer"])}</span><p class="answer">{esc(item["answer"])}</p></div>' if item.get("answer") else ""
        gap_html = f'<div class="question-gap"><span class="field-label">{esc(labels["gap"])}</span><p>{esc(item["gap"])}</p></div>' if item.get("gap") else ""
        quick_rows.append(f'<article id="question-{number}" class="card quick-card" tabindex="-1" aria-labelledby="question-{number}-title"><h3 id="question-{number}-title" class="question"><span class="question-number">{number:02d}</span>{esc(item["question"])}</h3>{question_meta}{why_html}{answer_html}{gap_html}{references(item.get("evidence"), mark_missing=True)}</article>')
        unresolved = f'<span class="index-answer-status" data-answer-status="{answer_status}">{esc(labels[answer_status])}</span>' if isinstance(answer_status, str) and answer_status in {"partial", "unanswered"} else ""
        question_links.append(f'<li><a class="question-jump" href="#question-{number}"><span class="question-index-number" aria-hidden="true">{number:02d}</span><span class="question-index-text">{esc(item["question"])}{unresolved}</span><span class="question-index-arrow" aria-hidden="true">↘</span></a></li>')
    question_index = f'<nav id="question-index" class="question-index" aria-labelledby="question-index-title"><div class="question-index-heading"><h2 id="question-index-title">{esc(labels["question_index"])}</h2><span>{esc(labels["question_index_hint"])}</span></div><ol>{"".join(question_links)}</ol></nav>' if question_links else ""
    if question_links:
        labels["quick"] = labels["question_details"]

    insights = records(digest.get("insights"))
    if not insights:
        insights = [{"title": item.get("claim"), "summary": item.get("speaker"), "evidence": item.get("evidence")} for item in records(evidence.get("claims")) if item.get("claim")]
    insight_rows = []
    for item in insights:
        if not (item.get("title") or item.get("summary")):
            continue
        index = len(insight_rows) + 1
        bullets = "".join(f"<li>{esc(value)}</li>" for value in strings(item.get("bullets")))
        body = f'<p>{esc(item["summary"])}</p>' if item.get("summary") else ""
        kind = item.get("kind")
        badge = f'<span class="kind">{esc(labels[kind])}</span>' if isinstance(kind, str) and kind in {"decision", "counterintuitive", "data", "method", "pitfall", "insight"} else ""
        insight_rows.append(f'<article class="card insight"><div class="insight-heading"><span class="index">{index:02d}</span><h3>{esc(item.get("title") or labels["claim"])}</h3>{badge}</div>{body}{f"<ul>{bullets}</ul>" if bullets else ""}{references(item.get("evidence"), mark_missing=True)}</article>')

    quote_rows = []
    for item in records(evidence.get("quotes"))[:3]:
        if not item.get("text"):
            continue
        speaker = f'<cite>— {esc(item["speaker"])}</cite>' if item.get("speaker") else ""
        refs = item.get("evidence") or [item]
        quote_rows.append(f'<article class="card quote"><blockquote><p>“{esc(item["text"])}”</p>{speaker}</blockquote>{references(refs, mark_missing=True)}</article>')

    action_rows = []
    for item in records(evidence.get("actions")):
        if not item.get("action"):
            continue
        context = f'<p class="context">{esc(item["for_whom"])}</p>' if item.get("for_whom") else ""
        for key in ("prerequisites", "risks"):
            values = strings(item.get(key))
            if values:
                context += f'<p class="context"><strong>{esc(labels[key])}: </strong>{esc(" / ".join(values))}</p>'
        action_rows.append(f'<article class="card action"><h3>{esc(item["action"])}</h3>{context}{references(item.get("evidence"), mark_missing=True)}</article>')

    chapter_rows = []
    for item in records(evidence.get("chapters")):
        chapter_rows.append(f'<li><strong>{esc(item.get("title"))}</strong><p>{esc(item.get("summary"))}</p>{references([item])}</li>')
    transcript_rows = []
    for index, item in enumerate(segments, 1) if include_transcript else []:
        segment_id = str(item.get("segment_id", index))
        start = seconds_value(item.get("start_seconds"))
        if start is None:
            start = seconds_value(item.get("start"))
        label = stamp(start) if start is not None else f'{labels["segment"]} {segment_id}'
        link = timestamp_url(source_url, start) if start is not None else None
        if link:
            timestamp_link_count += 1
        stamp_html = f'<a href="{esc(link)}" target="_blank" rel="noopener noreferrer">{esc(label)} ↗</a>' if link else esc(label)
        speaker = f'<strong class="speaker">{esc(item["speaker"])}</strong>' if item.get("speaker") else ""
        search = esc(f'{item.get("speaker") or ""} {item.get("text") or ""}'.lower())
        transcript_rows.append(f'<article id="segment-{esc(segment_id)}" class="segment" tabindex="-1" data-search="{search}"><div class="stamp">{stamp_html}</div><div>{speaker}<p>{esc(item.get("text"))}</p></div></article>')

    has_summary = bool(digest.get("takeaway") or evidence.get("summary") or quick_rows or insight_rows)
    pending = has_summary and finalized is not True and bool(bundle.get("status")) and bundle.get("status") != "analyzed"
    metadata = []
    if episode.get("show"):
        metadata.append(f'<span>{esc(episode["show"])}</span>')
    if episode.get("published"):
        metadata.append(f'<span>{esc(episode["published"])}</span>')
    duration = seconds_value(episode.get("duration_seconds"))
    if duration is None:
        duration = seconds_value(transcript.get("duration_seconds"))
    names = [str(item["name"]) for item in records(digest.get("participants")) if item.get("name")]
    if names:
        metadata.append(f'<span>{esc(" · ".join(names))}</span>')
    subtitle = f'<p class="episode-title">{esc(original_title)}</p>' if title != original_title else ""
    limitation_items = "".join(f"<li>{esc(value)}</li>" for value in strings(evidence.get("limitations")))
    limitations = section("limitations", f"<ul>{limitation_items}</ul>", "limitations") if limitation_items else ""
    open_items = "".join(f"<li>{esc(value)}</li>" for value in strings(digest.get("open_questions")))
    open_questions = section("open_questions", f'<div class="card open-questions"><ul>{open_items}</ul></div>') if open_items else ""
    chapter_content = section("chapters", f'<ol class="chapters">{"".join(chapter_rows)}</ol>') if chapter_rows else ""
    search_content = f'''<label for="search">{esc(labels["search"])}</label>
<div class="search-controls"><input id="search" type="search" placeholder="{esc(labels["placeholder"])}" autocomplete="off" aria-controls="segments"><button id="clear-search" class="button" type="button" disabled>{esc(labels["clear"])}</button></div>
<div id="result-count" role="status" aria-live="polite" data-all="{esc(labels["count_all"])}" data-match="{esc(labels["count_match"])}"></div>
<div id="search-empty" class="search-empty" hidden><strong>{esc(labels["empty_title"])}</strong><p>{esc(labels["empty_help"])}</p><button id="reset-search" class="button" type="button">{esc(labels["reset"])}</button></div>
<div id="segments">{"".join(transcript_rows)}</div>'''
    transcript_content = section("transcript", search_content) if transcript_rows else ""
    details_label = labels["details"] if transcript_rows else labels["details_chapters"]
    return_control = f'<div class="source-return"><a class="return-summary" href="#summary">← {esc(labels["return"])}</a></div>' if transcript_rows else ""
    details = f'<details class="source-details" id="source-details"><summary>{esc(details_label)}</summary><div class="source-content">{return_control}{chapter_content}{transcript_content}{return_control}</div></details>' if chapter_content or transcript_content else ""
    summary_content = "".join((
        section("quick", f'<div class="question-cards">{"".join(quick_rows)}</div>', count=len(quick_rows)) if quick_rows else "",
        section("insights", "".join(insight_rows), count=len(insight_rows)),
        section("quotes", "".join(quote_rows)), section("actions", "".join(action_rows)), open_questions,
        section("participants", f'<div class="grid">{"".join(participants)}</div>') if participants else "", limitations,
    ))
    takeaway_html = f'<div class="takeaway"><span class="kicker">{esc(labels["takeaway"] if has_summary else labels["pending_title"])}</span><p>{esc(takeaway)}</p>{references(digest.get("evidence") or digest.get("takeaway_evidence"), compact=True)}</div>'
    stats = []
    if has_summary:
        minutes = reading_minutes(takeaway_html + summary_content)
        stats.append(f'<span class="read-time" title="{esc(labels["reading_basis"])}">{esc(labels["reading"].format(n=minutes))}</span>')
    if duration:
        stats.append(f'<span>{esc(labels["duration"].format(n=math.ceil(duration / 60)))}</span>')
    if quick_rows:
        stats.append(f'<span>{esc(labels["questions_count"].format(n=len(quick_rows)))}</span>')
    if insight_rows:
        stats.append(f'<span>{esc(labels["insights_count"].format(n=len(insight_rows)))}</span>')
    reading_stats = f'<div class="reading-stats">{"".join(stats)}</div>' if stats else ""
    toolbar_buttons = []
    payload = fallback = ""
    if has_summary and not pending:
        markdown = markdown_summary(evidence, bundle, transcript, title, takeaway, labels)
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", title).strip(". ")[:100] or "podcast-summary"
        toolbar_buttons.extend((
            f'<button id="copy-summary" class="button primary" type="button" data-success="{esc(labels["copied"])}" data-manual="{esc(labels["copy_manual"])}">{esc(labels["copy"])}</button>',
            f'<button id="download-summary" class="button" type="button" data-filename="{esc(filename)}.md" data-success="{esc(labels["saved"])}" data-failure="{esc(labels["save_failed"])}">{esc(labels["save"])}</button>',
        ))
        payload = f'<pre id="summary-markdown" hidden>{esc(markdown)}</pre>'
        fallback = f'<div id="copy-fallback" class="copy-fallback" hidden><p>{esc(labels["copy_help"])}</p><label class="sr-only" for="copy-text">{esc(labels["copy_text"])}</label><textarea id="copy-text" readonly spellcheck="false"></textarea><button id="close-copy" class="button" type="button">{esc(labels["copy_close"])}</button></div>'
    if source_url:
        toolbar_buttons.append(f'<a class="button source-button" href="{esc(source_url)}" target="_blank" rel="noopener noreferrer">{esc(labels["source"])} ↗</a>')
    toolbar = f'<div class="toolbar">{"".join(toolbar_buttons)}</div>' if toolbar_buttons else ""
    feedback = f'<p id="toolbar-status" class="toolbar-feedback" role="status" aria-live="polite">{esc(labels["stale"]) if pending else ""}</p>' if toolbar_buttons or pending else ""
    nav_items = []
    for key, available in (("quick", quick_rows), ("insights", insight_rows), ("quotes", quote_rows), ("open_questions", open_items), ("source", details)):
        if available:
            target = "source-details" if key == "source" else key
            nav_items.append(f'<li><a href="#{target}">{esc(labels["nav_" + key])}</a></li>')
    nav = f'<nav class="section-nav" aria-label="{esc(labels["nav"])}"><ul>{"".join(nav_items)}</ul></nav>' if nav_items else ""
    script_tag = f"<script>{TOOLBAR_SCRIPT}{TRANSCRIPT_SCRIPT if transcript_rows else ''}</script>"
    page = f"""<!doctype html>
<html lang="{labels["language"]}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="data:,">
<meta name="description" content="{esc(takeaway)}"><title>{esc(title)} · Podcast Reader</title><style>{STYLE}</style></head>
<body id="top"><a class="skip" href="#summary">{esc(labels["skip"])}</a><div class="page">
<header class="hero{" question-led" if question_links else ""}"><div class="eyebrow">{esc(labels["core_question"] if core_question else labels["brand"])}</div><h1>{esc(title)}</h1>{subtitle}<div class="metadata">{"".join(metadata)}</div>
{question_index}{takeaway_html}{reading_stats}{toolbar}{feedback}{fallback}</header>{nav}
<main id="summary" tabindex="-1">{summary_content}{details}</main>
<footer><span>{esc(labels["footer"])}</span><a href="#top">{esc(labels["top"])} ↑</a></footer></div>{payload}{script_tag}</body></html>"""
    output = output.expanduser().resolve()
    atomic_write_text(output, page)
    return {
        "status": "rendered", "output": str(output), "segments": len(transcript_rows),
        "chapters": len(chapter_rows), "timestamp_links": timestamp_link_count > 0,
        "quick_takes": len(quick_rows), "insights": len(insight_rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode_dir")
    parser.add_argument("--output")
    parser.add_argument("--without-transcript", action="store_true", help="Omit full transcript content from the HTML")
    args = parser.parse_args()
    episode_dir = Path(args.episode_dir).expanduser().resolve()
    output = Path(args.output).expanduser().resolve() if args.output else episode_dir / "reader.html"
    try:
        result = render(episode_dir, output, include_transcript=not args.without_transcript)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
