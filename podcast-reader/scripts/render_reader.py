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
    },
}


STYLE = """
:root{color-scheme:dark;--bg:#0b0e13;--panel:#12161e;--panel-soft:#10141b;--ink:#e8e8e5;--muted:#969ba5;--gold:#e8c66b;--line:#262b34;--focus:#f5d67e}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.8 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
a{color:var(--gold);text-decoration:none}a:hover{text-decoration:underline}a:focus-visible,input:focus-visible,summary:focus-visible{outline:2px solid var(--focus);outline-offset:5px}
.skip{position:absolute;left:-9999px}.skip:focus{left:16px;top:16px;background:var(--panel);padding:10px;z-index:2}
.page{max-width:900px;margin:0 auto;padding:48px 32px 26px}.hero{text-align:center;padding:0 26px 34px;border-bottom:1px solid var(--line)}
.eyebrow{display:inline-block;border:1px solid #6a572d;border-radius:30px;padding:2px 14px;font-size:10px;letter-spacing:.24em;color:var(--gold)}
h1{font-size:clamp(27px,4.5vw,42px);line-height:1.45;font-weight:750;letter-spacing:.015em;color:var(--gold);margin:21px auto 15px;max-width:740px;text-wrap:balance}
.episode-title{font-size:12px;color:var(--muted);margin:0 auto 12px;max-width:660px}.metadata{display:flex;justify-content:center;flex-wrap:wrap;gap:8px;font-size:11px;color:var(--muted)}
.metadata span,.metadata a{border:1px solid var(--line);border-radius:4px;padding:2px 9px}.takeaway{margin:25px auto 0;max-width:680px;text-align:left;border-left:2px solid var(--gold);padding:3px 0 3px 17px}
.kicker{color:var(--gold);font-size:11px;letter-spacing:.08em;font-weight:650}.takeaway p{font-size:16px;margin:5px 0 0;line-height:1.8}
section{margin-top:31px}h2{font-size:17px;letter-spacing:.035em;margin:0 0 14px;padding-left:11px;border-left:3px solid var(--gold);line-height:1.25;color:var(--gold)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.card{background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:19px 20px;min-width:0}
.card h3{font-size:16px;line-height:1.6;color:var(--gold);margin:0 0 7px}.card p{margin:5px 0;font-size:13px;line-height:1.8}.participant .role{font-size:11px;color:var(--muted)}.participant p{color:#c2c5cc}
.quick-card .question{font-size:11px;color:var(--muted);margin-bottom:6px}.quick-card .answer{font-size:15px;line-height:1.65;font-weight:650;color:var(--gold)}
.insight{margin-top:12px}.insight:first-child{margin-top:0}.insight-heading{display:flex;gap:11px;align-items:baseline;flex-wrap:wrap}.index{font:12px/1.5 ui-monospace,monospace;color:#8d7847}.kind{font-size:10px;color:var(--muted);border:1px solid var(--line);padding:0 6px;border-radius:4px}
.insight ul,.open-questions ul{margin:9px 0 0;padding-left:18px;font-size:13px}.insight li,.open-questions li{padding-left:2px;margin:5px 0}.insight li::marker,.open-questions li::marker{color:var(--gold)}
.evidence{display:flex;gap:8px;flex-wrap:wrap;margin-top:13px;font:10px/1.7 ui-monospace,monospace;color:var(--muted)}.evidence a,.evidence span{padding:1px 6px;border:1px solid var(--line);border-radius:4px}.evidence a{color:#bda562}
blockquote{margin:0;padding:1px 0 1px 16px;border-left:2px solid #776232}blockquote p{font-size:16px!important;line-height:1.8!important}blockquote cite{font-size:11px;color:var(--muted);font-style:normal}
.quote+.quote,.action+.action{margin-top:12px}.action .context{color:var(--muted);font-size:12px}.limitations{color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:16px}.limitations ul{margin:0;padding-left:18px}
.source-details{margin-top:30px;border:1px solid var(--line);border-radius:9px;background:var(--panel-soft)}.source-details>summary{padding:17px 20px;cursor:pointer;color:var(--muted);font-size:13px}.source-content{padding:0 20px 20px}
.source-content h2{font-size:14px}.source-content section{margin-top:20px}.chapters{padding-left:20px;font-size:12px}.chapters li{margin:12px 0}.chapters p{color:var(--muted);margin:3px 0}
label{display:block;color:var(--muted);font-size:12px;margin-bottom:6px}input{display:block;width:100%;font:inherit;font-size:13px;background:var(--bg);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:10px 13px}#result-count{font-size:11px;color:var(--muted);margin:8px 0}
.segment{display:grid;grid-template-columns:82px 1fr;gap:14px;padding:14px 0;border-top:1px solid var(--line);font-size:12px}.segment[hidden]{display:none}.stamp{font:10px/1.8 ui-monospace,monospace;color:var(--muted)}.speaker{font-size:11px;color:var(--gold)}.segment p{margin:0;white-space:pre-wrap}.segment:target{background:#282315;outline:1px solid var(--gold);scroll-margin-top:20px}
footer{text-align:center;margin-top:30px;color:#737985;font-size:10px;letter-spacing:.04em}.card,.takeaway,blockquote{overflow-wrap:anywhere}
@media(max-width:600px){.page{padding:30px 18px 22px}.hero{padding:0 0 25px}h1{font-size:27px}.grid{gap:9px}.card{padding:15px 14px}.quick-card .answer{font-size:13px}.card h3{font-size:14px}.takeaway p{font-size:14px}section{margin-top:26px}h2{font-size:15px}.segment{grid-template-columns:1fr;gap:3px}.metadata{gap:5px}.source-content{padding:0 14px 16px}}
@media(max-width:380px){.grid{grid-template-columns:1fr}}
@media print{:root{color-scheme:light;--bg:#fff;--panel:#fff;--panel-soft:#fff;--ink:#171717;--muted:#555;--gold:#70521b;--line:#ddd}body{font-size:10pt}.page{max-width:none;padding:0}.hero{padding-bottom:20px}h1{font-size:25pt}.card,blockquote,.takeaway{break-inside:avoid;box-shadow:none}.card{border-color:#ddd}section{margin-top:20px}.source-details{display:none}.metadata a{display:none}a{color:inherit}.skip{display:none}footer{color:#777}.evidence a{color:#70521b}.participant p{color:#333}}
"""


def render(episode_dir: Path, output: Path, *, include_transcript: bool = True) -> dict[str, Any]:
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
    title = str(digest.get("headline") or original_title)
    takeaway = str(digest.get("takeaway") or evidence.get("summary") or labels["pending"])
    segments = records(transcript.get("segments"))
    segment_map = {str(item.get("segment_id", index)): item for index, item in enumerate(segments, 1)}
    timestamp_link_count = 0

    def references(items: Any, *, mark_missing: bool = False) -> str:
        nonlocal timestamp_link_count
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
            if link:
                entry = f'<a href="{esc(link)}" target="_blank" rel="noopener noreferrer" aria-label="{esc(labels["evidence"] + ": " + label)}">{esc(label)} ↗</a>'
                timestamp_link_count += 1
            elif ids and include_transcript:
                entry = f'<a class="segment-reference" href="#segment-{esc(anchor_id)}">{esc(label)}</a>'
            else:
                entry = f'<span>{esc(label)}</span>'
            if entry not in seen:
                links.append(entry)
                seen.add(entry)
        if not links and mark_missing:
            links.append(f'<span>{esc(labels["evidence_missing"])}</span>')
        return f'<div class="evidence">{"".join(links)}</div>' if links else ""

    def section(key: str, content: str, class_name: str = "") -> str:
        if not content:
            return ""
        return f'<section class="{esc(class_name)}" aria-labelledby="{key}-title"><h2 id="{key}-title">{esc(labels[key])}</h2>{content}</section>'

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
    for item in records(digest.get("quick_takes")):
        if not item.get("question") or not item.get("answer"):
            continue
        quick_rows.append(f'<article class="card quick-card"><div class="question">{esc(item["question"])}</div><div class="answer">{esc(item["answer"])}</div>{references(item.get("evidence"), mark_missing=True)}</article>')

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
        transcript_rows.append(f'<article id="segment-{esc(segment_id)}" class="segment" data-search="{search}"><div class="stamp">{stamp_html}</div><div>{speaker}<p>{esc(item.get("text"))}</p></div></article>')

    metadata = []
    if episode.get("show"):
        metadata.append(f'<span>{esc(episode["show"])}</span>')
    if episode.get("published"):
        metadata.append(f'<span>{esc(episode["published"])}</span>')
    duration = seconds_value(episode.get("duration_seconds"))
    if duration is None:
        duration = seconds_value(transcript.get("duration_seconds"))
    if duration:
        metadata.append(f'<span>{math.ceil(duration / 60)} {esc(labels["minutes"])}</span>')
    if source_url:
        metadata.append(f'<a href="{esc(source_url)}" target="_blank" rel="noopener noreferrer">{esc(labels["source"])} ↗</a>')
    subtitle = f'<p class="episode-title">{esc(original_title)}</p>' if title != original_title else ""
    limitation_items = "".join(f"<li>{esc(value)}</li>" for value in strings(evidence.get("limitations")))
    limitations = section("limitations", f"<ul>{limitation_items}</ul>", "limitations") if limitation_items else ""
    open_items = "".join(f"<li>{esc(value)}</li>" for value in strings(digest.get("open_questions")))
    open_questions = section("open_questions", f'<div class="card open-questions"><ul>{open_items}</ul></div>') if open_items else ""
    chapter_content = section("chapters", f'<ol class="chapters">{"".join(chapter_rows)}</ol>') if chapter_rows else ""
    transcript_content = section("transcript", f'<label for="search">{esc(labels["search"])}</label><input id="search" type="search" placeholder="{esc(labels["placeholder"])}" autocomplete="off"><div id="result-count" role="status" aria-live="polite"></div><div id="segments">{"".join(transcript_rows)}</div>') if transcript_rows else ""
    details_label = labels["details"] if transcript_rows else labels["details_chapters"]
    details = f'<details class="source-details" id="source-details"><summary>{esc(details_label)}</summary><div class="source-content">{chapter_content}{transcript_content}</div></details>' if chapter_content or transcript_content else ""
    # JSON strings below are labels from the fixed dictionary, never user-authored data.
    all_label, match_label = json.dumps(labels["count_all"], ensure_ascii=False), json.dumps(labels["count_match"], ensure_ascii=False)
    script = """const input=document.querySelector('#search'),rows=[...document.querySelectorAll('.segment')],count=document.querySelector('#result-count');
function filter(){const q=input.value.trim().toLowerCase();let visible=0;for(const row of rows){const show=!q||row.dataset.search.includes(q);row.hidden=!show;if(show)visible++}count.textContent=(q?MATCH_LABEL:ALL_LABEL).replace('{n}',q?visible:rows.length)}
if(input){input.addEventListener('input',filter);filter()}
function revealSource(){if(!location.hash.startsWith('#segment-'))return;const target=document.getElementById(location.hash.slice(1)),details=document.getElementById('source-details');if(target&&details){details.open=true;if(input){input.value='';filter()}target.scrollIntoView({block:'center'})}}
window.addEventListener('hashchange',revealSource);document.querySelectorAll('.segment-reference').forEach(link=>link.addEventListener('click',()=>{const details=document.getElementById('source-details');if(details)details.open=true;if(input){input.value='';filter()}}));revealSource();""".replace("MATCH_LABEL", match_label).replace("ALL_LABEL", all_label)
    script_tag = f"<script>{script}</script>" if transcript_rows else ""
    page = f"""<!doctype html>
<html lang="{labels["language"]}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="icon" href="data:,">
<meta name="description" content="{esc(takeaway)}"><title>{esc(title)} · Podcast Reader</title><style>{STYLE}</style></head>
<body><a class="skip" href="#summary">{esc(labels["skip"])}</a><div class="page">
<header class="hero"><div class="eyebrow">{esc(labels["brand"])}</div><h1>{esc(title)}</h1>{subtitle}<div class="metadata">{"".join(metadata)}</div>
<div class="takeaway"><span class="kicker">{esc(labels["takeaway"])}</span><p>{esc(takeaway)}</p>{references(digest.get("evidence") or digest.get("takeaway_evidence"))}</div></header>
<main id="summary">{section("participants", f'<div class="grid">{"".join(participants)}</div>') if participants else ""}
{section("quick", f'<div class="grid">{"".join(quick_rows)}</div>') if quick_rows else ""}
{section("insights", "".join(insight_rows))}{section("quotes", "".join(quote_rows))}{section("actions", "".join(action_rows))}{open_questions}{limitations}{details}</main>
<footer>{esc(labels["footer"])}</footer></div>{script_tag}</body></html>"""
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
