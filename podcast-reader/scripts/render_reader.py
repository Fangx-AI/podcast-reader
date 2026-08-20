#!/usr/bin/env python3
"""Render an accessible, searchable, timestamp-linked standalone episode reader."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import sys
from typing import Any
import urllib.parse

from runtime_utils import atomic_write_text


def timestamp_url(source_url: str | None, value: float) -> str | None:
    if not source_url or not source_url.startswith(("http://", "https://")):
        return None
    parsed = urllib.parse.urlsplit(source_url)
    host = (parsed.hostname or "").casefold()
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    seconds = max(0, int(value))
    if host == "youtu.be" or host.endswith("youtube.com"):
        query = [(key, item) for key, item in query if key != "t"] + [("t", f"{seconds}s")]
    elif host == "b23.tv" or host.endswith("bilibili.com"):
        query = [(key, item) for key, item in query if key != "t"] + [("t", str(seconds))]
    else:
        fragment = f"t={seconds}"
        return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, fragment))
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), ""))


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def render(episode_dir: Path, output: Path) -> dict[str, Any]:
    episode_dir = episode_dir.expanduser().resolve()
    transcript = load(episode_dir / "transcript.json")
    bundle = load(episode_dir / "bundle.json")
    evidence = load(episode_dir / "evidence.json") if (episode_dir / "evidence.json").is_file() else {}
    source_url = bundle.get("source_input") if isinstance(bundle.get("source_input"), str) else None
    title = str((evidence.get("episode") or {}).get("title") or (bundle.get("resolution") or {}).get("title") or episode_dir.name)
    summary = str(evidence.get("summary") or "可搜索逐字稿已准备完成。")
    chapter_rows = []
    for item in evidence.get("chapters", []) if isinstance(evidence.get("chapters"), list) else []:
        if not isinstance(item, dict):
            continue
        chapter_rows.append(f"<li><strong>{html.escape(str(item.get('start') or ''))}</strong> {html.escape(str(item.get('title') or ''))}<span>{html.escape(str(item.get('summary') or ''))}</span></li>")
    transcript_rows = []
    for item in transcript.get("segments", []):
        if not isinstance(item, dict):
            continue
        segment_id = int(item.get("segment_id") or len(transcript_rows) + 1)
        stamp = str(item.get("start") or "--:--")
        link = timestamp_url(source_url, float(item.get("start_seconds") or 0))
        stamp_html = f'<a href="{html.escape(link)}" target="_blank" rel="noopener">{html.escape(stamp)}</a>' if link else html.escape(stamp)
        speaker = f'<strong class="speaker">{html.escape(str(item.get("speaker")))}</strong>' if item.get("speaker") else ""
        search = html.escape(f"{item.get('speaker') or ''} {item.get('text') or ''}".casefold(), quote=True)
        transcript_rows.append(f'<article id="segment-{segment_id}" class="segment" data-search="{search}"><div class="stamp">{stamp_html}</div><div>{speaker}<p>{html.escape(str(item.get("text") or ""))}</p></div></article>')
    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} · Podcast Reader</title>
<style>
:root{{--bg:#f7f7fb;--panel:#fff;--text:#171721;--muted:#626273;--accent:#5848d8;--border:#dedee8;--focus:#ff9f1c}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.65 system-ui,-apple-system,"Segoe UI",sans-serif}}a{{color:var(--accent)}}a:focus,input:focus,button:focus{{outline:3px solid var(--focus);outline-offset:3px}}.skip{{position:absolute;left:-9999px}}.skip:focus{{left:1rem;top:1rem;background:#fff;padding:.7rem;z-index:10}}header,main{{max-width:1000px;margin:auto;padding:28px 24px}}header h1{{font-size:clamp(2rem,5vw,3.5rem);line-height:1.08;margin:.2rem 0 1rem}}.eyebrow{{color:var(--accent);font-weight:750;letter-spacing:.08em;text-transform:uppercase}}.summary,.chapters,.transcript{{background:var(--panel);border:1px solid var(--border);border-radius:18px;padding:24px;margin:20px 0;box-shadow:0 8px 30px rgba(30,25,70,.06)}}label{{font-weight:700;display:block;margin-bottom:8px}}input{{width:100%;font:inherit;border:1px solid #aaaabd;border-radius:12px;padding:13px 15px}}#result-count{{color:var(--muted);margin:.6rem 0}}.segment{{display:grid;grid-template-columns:92px 1fr;gap:18px;padding:18px 0;border-top:1px solid var(--border)}}.segment:first-of-type{{border-top:0}}.stamp{{font-variant-numeric:tabular-nums;font-weight:700}}.speaker{{display:block;color:var(--accent)}}.segment p{{margin:.15rem 0}}.chapters li{{margin:.7rem 0}}.chapters li span{{display:block;color:var(--muted)}}footer{{text-align:center;color:var(--muted);padding:30px}}@media(max-width:600px){{.segment{{grid-template-columns:1fr;gap:2px}}header,main{{padding:20px 14px}}}}
</style></head><body><a class="skip" href="#transcript">跳到逐字稿</a>
<header><div class="eyebrow">Podcast Reader</div><h1>{html.escape(title)}</h1><p>{html.escape(summary)}</p></header>
<main><section class="chapters" aria-labelledby="chapters-title"><h2 id="chapters-title">章节</h2><ol>{''.join(chapter_rows) or '<li>尚未生成结构化章节。</li>'}</ol></section>
<section class="transcript" id="transcript" aria-labelledby="transcript-title"><h2 id="transcript-title">可搜索逐字稿</h2><label for="search">搜索节目内容</label><input id="search" type="search" placeholder="输入人物、概念或原话" autocomplete="off"><div id="result-count" role="status" aria-live="polite"></div><div id="segments">{''.join(transcript_rows)}</div></section></main>
<footer>由 Podcast Reader 生成。点击时间戳可返回原平台对应位置。</footer>
<script>const input=document.querySelector('#search'),rows=[...document.querySelectorAll('.segment')],count=document.querySelector('#result-count');function filter(){{const q=input.value.trim().toLocaleLowerCase();let visible=0;for(const row of rows){{const show=!q||row.dataset.search.includes(q);row.hidden=!show;if(show)visible++}}count.textContent=q?`找到 ${{visible}} 段`:`共 ${{rows.length}} 段`;}}input.addEventListener('input',filter);filter();</script></body></html>"""
    output = output.expanduser().resolve()
    atomic_write_text(output, page)
    return {"status": "rendered", "output": str(output), "segments": len(transcript_rows), "chapters": len(chapter_rows), "timestamp_links": bool(source_url)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("episode_dir")
    parser.add_argument("--output")
    args = parser.parse_args()
    episode_dir = Path(args.episode_dir).expanduser().resolve()
    output = Path(args.output).expanduser().resolve() if args.output else episode_dir / "reader.html"
    try:
        result = render(episode_dir, output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
