# Output contract

Human-readable output is Markdown. JSON is the canonical interchange format for retrieval and structured evidence. Use `null` for unknown values; never invent them.

## Episode bundle

```text
<episode_dir>/
├── bundle.json               # state, provenance, inventory, warnings, next actions
├── source.json               # stable source metadata
├── source-info.json          # compact platform metadata
├── transcript-raw.*          # immutable original transcript/captions
├── transcript.json           # normalized segment model
├── transcript.md             # readable transcript
├── transcript.srt/.vtt       # subtitle exports when timed
├── chunks.json               # retrieval index
├── analysis.md               # polished analysis
├── summary.md                # optional standalone summary
├── evidence.json             # claims/chapters/quotes/actions/entities/glossary
├── *.csv                     # optional table exports
└── frames/                   # optional visual lane
    ├── manifest.json
    ├── contact-sheet.jpg
    └── frame-*.jpg
```

`bundle.json` also records the requested mode/language so cache reuse cannot satisfy a deeper request with a metadata-only result. Stored media/transcript URLs must be provenance-safe: remove credentials and temporary, signed, or tracking query values.

## Normalized transcript

```json
{
  "schema_version": "1.0",
  "method": "publisher_transcript|human_captions|platform_captions|automatic_captions|generated|user_provided",
  "language": "zh-CN",
  "segment_count": 2,
  "timed_segment_count": 2,
  "speakers": ["Speaker 1"],
  "segments": [
    {
      "segment_id": 1,
      "start": "00:00:01",
      "end": "00:00:05",
      "start_seconds": 1.0,
      "end_seconds": 5.0,
      "speaker": "Speaker 1",
      "language": "zh-CN",
      "confidence": null,
      "text": "..."
    }
  ]
}
```

## Evidence JSON

```json
{
  "schema_version": "1.0",
  "episode": {
    "title": "",
    "show": "",
    "published": null,
    "duration_seconds": null,
    "source_url": ""
  },
  "summary": "",
  "chapters": [
    {"start": "00:00:00", "end": "00:12:30", "title": "", "summary": "", "speakers": []}
  ],
  "claims": [
    {
      "claim": "",
      "speaker": null,
      "kind": "fact|opinion|anecdote|prediction|recommendation|synthesis",
      "support": "stated|illustrated|argued|asserted|contradicted",
      "confidence": "high|medium|low",
      "verification": "not_checked|supported|mixed|contradicted|outdated|not_verifiable",
      "evidence": [{"start": "00:00:00", "end": "00:00:00", "segment_ids": [1], "label": "transcript indicates"}]
    }
  ],
  "quotes": [{"text": "", "speaker": null, "start": "00:00:00", "end": "00:00:00"}],
  "actions": [{"action": "", "for_whom": "", "prerequisites": [], "risks": [], "evidence": []}],
  "entities": [{"name": "", "type": "person|organization|product|book|paper|concept|tool", "context": "", "evidence": []}],
  "glossary": [{"source_term": "", "preferred_term": "", "type": "", "note": "", "evidence": []}],
  "visual_evidence": [{"timestamp": "00:00:00", "observation": "", "interpretation": "", "confidence": "high|medium|low"}],
  "limitations": []
}
```

All non-empty evidence references must resolve to a transcript segment or sampled visual frame.

## Markdown design rules

Use [../assets/analysis-template.md](../assets/analysis-template.md). Optimize for scanning:

- begin with conclusion, not process narration;
- place episode metadata in a compact table;
- use one consistent timestamp format;
- keep dense claim/evidence data in tables;
- keep paragraphs short and headings descriptive;
- distinguish source content, synthesis, and external verification with explicit labels;
- omit empty sections instead of leaving placeholders;
- end with limitations and processing notes.

## CSV exports

Use UTF-8 with BOM when the target is Excel. One file per entity type is clearer than a mixed table. Flatten evidence as semicolon-separated timestamp ranges and keep list fields as `; `-separated text.

Recommended files: `chapters.csv`, `claims.csv`, `quotes.csv`, `actions.csv`, `entities.csv`, and `glossary.csv`.

## Validation

`validate_bundle.py` checks structural consistency and artifact paths. `validate_notes.py --strict` checks report structure, timestamps, quote evidence, uncertainty, and unresolved placeholders. A report is not complete until relevant validators pass.
