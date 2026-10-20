# Output contract

Default `summary` mode has one authored source: **`evidence.json`**. The current Agent writes it; the finalizer validates it and generates **`summary.md`** and **`reader.html`**, plus `analysis.md` as a compatibility copy. Do not independently maintain multiple versions of the summary.

Use actual source metadata and `null` for unknown values. The examples below describe structure; their prose is illustrative and must be replaced with source-grounded content.

## Episode bundle

```text
<episode_dir>/
├── summary.md                # required primary text deliverable in summary mode
├── reader.html               # required primary reading-page deliverable
├── evidence.json             # canonical authored digest and references
├── analysis.md               # generated compatibility copy in summary mode
├── bundle.json               # state, provenance, artifact inventory, warnings
├── source.json               # stable source metadata
├── source-info.json          # platform metadata when available
├── transcript-raw.*          # immutable original transcript/captions
├── transcript.json           # normalized segments, with real timestamps if available
├── transcript.md             # readable source text
├── chunks.json               # index for reviewing long sources
├── transcript-quality.json   # quality metrics and spot-check queue
└── analysis-handoff.json     # current Agent's completion instructions
```

Other existing artifacts such as subtitle exports, translations, CSV, or video frames may remain in a bundle, but are not required parts of the default reading experience. `bundle.json` records the requested mode and output language. `ready_for_analysis` is a preparation state, not completed delivery.

Stored URLs must exclude credentials and temporary, signed, or tracking query values. Share exports must not expose local absolute paths or carry full transcripts by default.

## Normalized transcript

```json
{
  "schema_version": "1.0",
  "method": "user_provided",
  "language": "zh-CN",
  "segment_count": 1,
  "timed_segment_count": 1,
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
      "text": "Source text."
    }
  ]
}
```

Supported method values include `publisher_transcript`, `human_captions`, `platform_captions`, `automatic_captions`, `generated`, and `user_provided`. Untimed source segments keep their stable `segment_id`; time fields remain unknown rather than being invented.

## Evidence JSON for the default summary

```json
{
  "schema_version": "2.0",
  "episode": {
    "title": "Source episode title",
    "show": null,
    "published": null,
    "duration_seconds": null,
    "source_url": "https://example.com/episode"
  },
  "summary": "A concise source-grounded takeaway.",
  "digest": {
    "headline": "A specific headline expressing the central question",
    "core_question": "What central problem does this episode help the listener examine?",
    "takeaway": "The episode's main answer, including its decisive condition.",
    "evidence": [{"start": "00:00:01", "end": "00:00:05", "segment_ids": [1]}],
    "participants": [
      {"name": "Source-confirmed name", "role": "Guest", "description": "Source-confirmed introduction."}
    ],
    "quick_takes": [
      {
        "question": "A concrete question the listener would want answered?",
        "why_it_matters": "The choice or misunderstanding that makes this question important.",
        "question_origin": "synthesized",
        "answer_status": "partial",
        "answer": "The direct answer, followed by its essential reason or caveat.",
        "gap": "The condition, evidence or decision threshold the episode leaves unresolved.",
        "evidence": [{"start": "00:00:01", "end": "00:00:05", "segment_ids": [1]}]
      }
    ],
    "insights": [
      {
        "kind": "insight",
        "title": "A finding, rather than a generic topic label",
        "summary": "Explain the finding, its evidence, and why it matters.",
        "bullets": ["An optional detail, example, step, or condition."],
        "evidence": [{"start": "00:00:01", "end": "00:00:05", "segment_ids": [1]}]
      }
    ],
    "open_questions": []
  },
  "chapters": [],
  "claims": [],
  "quotes": [],
  "actions": [],
  "entities": [],
  "glossary": [],
  "visual_evidence": [],
  "limitations": ["State concrete source or transcription limits when applicable."]
}
```

### Digest requirements

| Field | Contract |
|---|---|
| `headline` | Required nonempty string, at most 120 characters |
| `core_question` | Nonempty string of at most 160 characters for new question-led digests; supported by `digest.evidence`. Legacy digests may omit the field; an explicit `null` or empty string is invalid |
| `takeaway` | Required nonempty string, at most 400 characters |
| `evidence` | 1–12 references supporting the core question and takeaway; each answer and insight uses the same reference-list bounds |
| `participants` | Optional list, at most 8; required name at most 100 characters, optional role at most 100, optional description at most 300; all must come from source metadata or introductions |
| `quick_takes` | 1–6 question/answer items, each with nonempty evidence; questions at most 160 characters, answers at most 500 |
| `quick_takes[].why_it_matters` | Nonempty string at most 300 characters; required when `core_question` is present |
| `quick_takes[].question_origin` | `explicit` for a question actually raised in the episode, or `synthesized` for an editorial question derived from its discussion; required when `core_question` is present |
| `quick_takes[].answer_status` | `answered`, `partial`, or `unanswered`; required when `core_question` is present. This describes what the episode answers, not whether that answer is externally verified |
| `quick_takes[].gap` | At most 300 characters. Nonempty and required for `partial` or `unanswered`; absent, `null`, or empty for `answered` |
| `insights` | 1–7 items with title, summary, and nonempty evidence; titles at most 160 characters, summaries at most 700 |
| `insights[].bullets` | Optional, at most 4 strings per insight; each at most 300 characters |
| `insights[].kind` | Optional: `decision`, `counterintuitive`, `data`, `method`, `pitfall`, or `insight` |
| `open_questions` | Optional, at most 5 strings of at most 300 characters; only questions the episode actually leaves unresolved |

The overall rendered natural-language text budget is at most 12,000 characters, including metadata and optional sections checked by the digest validator. These are ceilings, not writing targets. Aim for a 3–5 minute read, usually 3–6 key questions and 3–7 insights; short or sparse sources should use fewer. Never pad the content to meet editorial targets.

New summaries start from the episode's central problem and a small set of distinct questions. Do not turn every section heading into a question or label an editor's synthesized question as a verbatim question from the source. For `unanswered`, `answer` should describe what the episode does establish and explicitly state that no answer is provided; `gap` names what remains missing. Do not supply an invented conclusion to make a question appear answered.

When `core_question` is present, every question must include its importance, origin and answer status. Legacy digests without `core_question` remain valid and do not receive guessed statuses. New question fields, when supplied on a legacy digest, are still checked; `partial` and `unanswered` always require `gap`. Questions that become identical after Unicode normalization, case folding, and removal of whitespace and punctuation are rejected. Semantic redundancy beyond that remains an editorial review task; the validator does not infer question quality from punctuation or length.

New handoffs set `summary_contract.question_contract_version: 1` and require `core_question`. Completion preserves `bundle.question_contract_version: 1`; validators enforce this requirement with `validate_digest(..., require_questions=True)`. The default flag remains false for existing bundles, so introducing the new structure does not invalidate legacy summaries solely because they lack these fields.

Participants are optional. Do not invent credentials or biographies, infer identity from a voice, or copy a name from an unrelated screenshot. If an unresolved question needs explanation or references, discuss it in a cited answer or insight rather than presenting the Agent's speculation as the episode's open question.

Use `kind` labels only when they help a reader scan; there is no requirement to supply every type. High-value information can include meaningful narrative or cultural observations as well as methods and data.

### Evidence references

The core question, takeaway, each question's answer and boundaries, and each insight must cite source segments. The core question shares `digest.evidence` with the takeaway. A typical timed reference is:

```json
{"start": "00:12:10", "end": "00:12:38", "segment_ids": [42, 43]}
```

For untimed TXT/Markdown, use real segment IDs without invented times:

```json
{"segment_ids": [3, 4]}
```

All IDs must resolve in `transcript.json`. Provided time ranges must be ordered, within the source timeline, and consistent with the cited segments. Use the smallest sufficient passage; include multiple references when a conclusion combines distant passages. Source references make a claim checkable but do not externally verify its truth.

### Optional supporting structures

Keep these empty when they add no value. Existing integrations can still use them:

```json
{
  "chapters": [
    {"start": "00:00:00", "end": "00:12:30", "title": "Topic", "summary": "Source summary", "speakers": []}
  ],
  "claims": [
    {
      "claim": "A normalized source claim or explicitly labeled synthesis",
      "speaker": null,
      "kind": "synthesis",
      "support": "argued",
      "confidence": "medium",
      "verification": "not_checked",
      "evidence": [{"segment_ids": [1]}]
    }
  ],
  "quotes": [
    {"text": "Exact short source text", "speaker": null, "start": "00:00:01", "end": "00:00:05", "segment_ids": [1]}
  ],
  "actions": [
    {"action": "Source-supported advice", "for_whom": "Applicable audience", "prerequisites": [], "risks": [], "evidence": [{"segment_ids": [1]}]}
  ],
  "entities": [
    {"name": "Name", "type": "concept", "context": "Source context", "evidence": [{"segment_ids": [1]}]}
  ],
  "glossary": [
    {"source_term": "Original term", "preferred_term": "Translation", "type": "concept", "note": "Meaning in context", "evidence": [{"segment_ids": [1]}]}
  ],
  "visual_evidence": [
    {"timestamp": "00:00:01", "observation": "Literal visual content", "interpretation": "Separately labeled inference", "confidence": "medium"}
  ]
}
```

Claim `kind`: `fact|opinion|anecdote|prediction|recommendation|synthesis`. Claim `support`: `stated|illustrated|argued|asserted|contradicted`. Confidence: `high|medium|low`. Verification: `not_checked|supported|mixed|contradicted|outdated|not_verifiable`. Entity type: `person|organization|product|book|paper|concept|tool`.

Quote count is at most 3 in the default summary, each at most 500 characters. Each short quote must be an exact substring of the referenced transcript window. Optional actions are limited to 5, chapters to 20, and limitations to 12. Chapters must be chronological and non-overlapping and require real timestamps; omit them for untimed text. Actions and entity references must resolve to source segments. Do not manufacture advice for narrative or fictional material.

## Rendering and validation

Use [the editorial template](../assets/analysis-template.md) and [the summary workflow](analysis-workflows.md). The reading order is: title → **the episode's core question** → **numbered question list with the episode's answer statuses** → one-sentence takeaway → each question's importance, source-grounded answer, unresolved gap when applicable, and original references → supporting high-value insights. Source metadata and supporting material follow the main reading sequence. Legacy summaries show their question list without an invented core question or answer status. Chinese and English outputs follow the same structure.

```text
python "{skill_dir}/scripts/finalize_bundle.py" <episode_dir>
python "{skill_dir}/scripts/validate_bundle.py" <episode_dir>
```

Finalization is the generation gate. Correct `evidence.json` and rerun it when changing summary content. The default bundle is complete only when evidence and generated outputs pass validation. Do not report success merely because ingestion or transcription completed.

The bundle stores `analysis_mode`, `output_language`, primary `deliverables`, and SHA-256 `deliverable_hashes` for the generated summary and reader. Validation checks the Markdown against the digest and verifies both output hashes. An old research bundle, a different requested language, a missing output, or a damaged reader reopens the Agent handoff while retaining the source transcript.

`quick`, `standard`, and `deep` remain explicit legacy compatibility modes with their existing report contracts. The default `summary` contract does not require a deep report, argument map, external research, or a full translated transcript.
