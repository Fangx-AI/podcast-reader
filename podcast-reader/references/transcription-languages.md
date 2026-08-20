# Transcription, diarization, and multilingual policy

## Transcript quality ladder

Record one method in `source.json`/`transcript.json`:

| Method | Typical confidence | Required caveat |
|---|---:|---|
| `user_provided` / `publisher_transcript` | High | May be edited rather than verbatim |
| `human_captions` | High | Timing may be approximate |
| `platform_captions` | Medium–high | Identify human vs automatic when known |
| `automatic_captions` | Medium | Names, numbers, code, and punctuation need checking |
| `generated` | Medium | Model, language, diarization, and audio quality affect accuracy |
| `metadata_only` | Low for content | Dialogue and claims cannot be verified |

Preserve `transcript-raw.*` before normalization. The normalizer accepts SRT, VTT, ASS, TTML, LRC, YouTube JSON3, common JSON segment shapes, TXT, and Markdown, then creates a stable segment model with numeric and display timestamps, text, speaker, language, and optional confidence.

## Diarization

Enable diarization for interviews, panels, calls, debates, or any recording with multiple voices. Use known-speaker hints only when the source identifies participants. Map diarized labels to names only when introductions, show metadata, or repeated context make the mapping defensible.

Never infer identity from voice alone. Use `Speaker 1`, `Speaker 2`, etc. when uncertain. If overlapping speech or music makes a turn unreliable, mark that segment rather than forcing attribution.

## Long recordings

- Keep provider-side chunking enabled for long audio.
- Preserve timestamps across chunk boundaries.
- Add a small overlap when transcription chunks are processed independently.
- Reconcile duplicated overlap text during normalization.
- Check joins around speaker changes and cut-off sentences.

## Multilingual behavior

Detect and record the source language. If the user writes Chinese without specifying output language, write the analysis in Chinese while preserving proper nouns and important original wording.

For mixed-language material:

1. Keep each segment's original text.
2. Record language per segment when reliably known.
3. Translate into a separate field/file; never replace the original.
4. Preserve timestamps and speaker labels.
5. Keep a glossary for names, products, organizations, acronyms, and technical terms.
6. Mark transliteration or translation choices that are genuinely ambiguous.

Recommended glossary fields:

| Field | Meaning |
|---|---|
| `source_term` | Exact source-language form |
| `preferred_term` | Chosen output-language form |
| `type` | Person, company, product, paper, book, concept, acronym |
| `note` | Meaning or translation rationale |
| `evidence` | First or clearest timestamp |

## Quality checks

Spot-check transcript segments containing:

- speaker introductions and role changes;
- dates, prices, percentages, measurements, and rankings;
- proper nouns, acronyms, URLs, commands, and code;
- direct quotes selected for the final report;
- claim-changing negation such as “not”, “never”, “不会”, or “并非”.

Use confidence labels at segment or report level. Do not turn ASR uncertainty into confident prose.
