# Podcast Reader v2.0.1

<div align="center">

<img src="podcast-reader/assets/icon-small.svg" width="88" alt="Podcast Reader icon">

## 🎧 Understand long podcasts fast, ask about the content, and find key moments later

**One link is enough.** Get the key ideas when you do not have time to finish, ask a specific question when that is all you need, and return to the exact source moment when a half-remembered point comes back months later.

[![Release](https://img.shields.io/github/v/release/Fangx-AI/podcast-reader?style=flat-square&color=2563eb)](https://github.com/Fangx-AI/podcast-reader/releases/latest)
[![CI](https://img.shields.io/github/actions/workflow/status/Fangx-AI/podcast-reader/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/Fangx-AI/podcast-reader/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/github/license/Fangx-AI/podcast-reader?style=flat-square)](LICENSE)
![API Key](https://img.shields.io/badge/Cloud_API_Key-optional-16a34a?style=flat-square)

[Get started](#30-second-setup) · [Example questions](#ask-it-like-this) · [What you get](#what-you-get) · [中文](README.md) · [English](README.en.md) · [Documentation](docs/README.md)

</div>

> [!TIP]
> Most users do not need a cloud transcription API key. Public captions are used when available; otherwise Podcast Reader can use the host Agent's transcription capability or run transcription locally.

---

## What it helps you do

| When this happens | Podcast Reader helps by | What you save |
|---|---|---|
| You find a two- or three-hour episode | Surfaces its topics, chapters, main ideas, and key moments | Hours of listening just to decide whether it is worth your time |
| You care about one specific question | Searches the whole episode, answers directly, and cites the relevant time | Scrubbing through the player and replaying fragments |
| You remember an idea but not the episode or minute | Retrieves the passage from a keyword or natural-language description | Re-listening or searching old notes by hand |
| The episode is in another language | Translates and explains terms while preserving the source timeline | Extra comprehension effort without losing the original context |
| You want notes or research material | Exports Markdown, subtitles, JSON, CSV, and a reader page | Copying, cleaning, and formatting everything yourself |

It does not ask you to build a complicated knowledge-management system first. It does something simpler: **turn long, linear media into content you can understand quickly, question naturally, and find again.**

## Ask it like this

No special command vocabulary or configuration interview is required. Say what you want in ordinary language.

| Your goal | A prompt you can copy |
|---|---|
| Get the gist | `Help me understand this episode in five minutes: <link>` |
| Decide whether to listen | `What is this episode about, and which three moments are most worth hearing?` |
| Ask about the content | `How does the guest answer the question about meaning in life? Explain it in context.` |
| Find a remembered idea | `I remember a point about the individual and cosmic perspectives. Find the passage and timestamp.` |
| Map disagreements | `Where do the host and guest disagree? Cite every point to the episode.` |
| Understand another language | `Translate this into Chinese while preserving important English terms and timestamps.` |
| Save or share notes | `Export a Notion-friendly Markdown report with chapters and source links.` |
| Research deeply | `Check the major claims and separate episode evidence, your analysis, and external verification.` |

Once processing is complete, keep asking follow-up questions without sending the link or transcribing the episode again.

## 30-second setup

### 1. Install once

~~~bash
git clone https://github.com/Fangx-AI/podcast-reader.git
cd podcast-reader
python podcast-reader/scripts/install_skill.py --json
~~~

To update an existing installation, opt in explicitly. The installer preserves a timestamped backup first.

~~~bash
python podcast-reader/scripts/install_skill.py --force --json
~~~

You can also download the [latest release](https://github.com/Fangx-AI/podcast-reader/releases/latest) and copy its <code>podcast-reader/</code> folder into a Skills directory discovered by your Agent. Use <code>--target</code> for a custom Skills directory.

| Client | Common location |
|---|---|
| Codex | <code>~/.codex/skills/podcast-reader/</code> |
| Agent Skills-compatible clients | <code>.agents/skills/podcast-reader/</code> |

### 2. Send a link

~~~text
Use $podcast-reader to help me understand this episode quickly: https://...
~~~

That is enough. The skill selects public captions or available audio and answers in your language. Replace “understand quickly” with “analyze deeply,” “answer this question,” or “help me find a remembered point” whenever needed.

### 3. Optional machine check

~~~bash
python podcast-reader/scripts/doctor.py --json
~~~

Doctor is offline and distinguishes installed readiness from bootstrap capability. It reports whether FFmpeg, yt-dlp, local transcription, storage, or output permissions need attention.

> [!NOTE]
> The first local transcription run for an episode without captions may need to download FFmpeg, isolated dependencies, or a speech model. Doctor tells you exactly what the machine is missing and never asks you to paste an API key into chat.

## Process once, come back anytime

Podcast Reader keeps a local, timestamped content bundle for each episode. It is not a one-shot summary: skim the episode today, ask follow-up questions tomorrow, and search for a remembered point months later.

~~~mermaid
flowchart LR
    A[One link or local file] --> B[Read and organize the episode]
    B --> C[Understand it quickly]
    B --> D[Ask a specific question]
    B --> E[Find an old idea]
    B --> F[Translate or export]
    C --> G[Return to source time]
    D --> G
    E --> G
~~~

On later questions, the skill reuses existing artifacts instead of downloading or transcribing the episode again without a reason.

## What you get

| Result | Why it is useful |
|---|---|
| **A readable episode overview** | Learn the subject, conclusions, and whether it deserves more of your time |
| **A timestamped chapter map** | Jump to the part you care about instead of scrubbing blindly |
| **Persistent episode Q&A** | Keep asking about people, claims, examples, and disagreements |
| **A searchable transcript reader** | Find a half-remembered line and return to its source moment |
| **Timestamp-preserving translations** | Understand another language without losing terms or source alignment |
| **Markdown and structured exports** | Save to Notion or Obsidian, or continue into research and writing |

Answers lead with the conclusion and then cite the smallest useful time range. If the episode does not contain enough evidence, the skill says so instead of inventing a position.

### How it differs from a summary or transcript

| Capability | One-shot summary | Typical transcript | Podcast Reader |
|---|:---:|:---:|:---:|
| Understand the whole episode quickly | ✓ | — | ✓ |
| Read the complete text | — | ✓ | ✓ |
| Keep asking episode-specific questions | — | — | ✓ |
| Find old ideas in natural language | — | Manual search | ✓ |
| Return to source time for verification | Rare | Varies | ✓ |
| Analyze chapters, arguments, and disagreement | Basic | — | ✓ |
| Translate while preserving timeline mapping | Rare | Varies | ✓ |
| Export Markdown, JSON, and subtitles | Rare | Varies | ✓ |

## How it works internally

~~~mermaid
flowchart LR
    A[URL or local file] --> B[Resolve source]
    B --> C{Public transcript?}
    C -->|Yes| D[Normalize transcript]
    C -->|No| E[Acquire public or authorized audio]
    E --> F[Transcribe and assess quality]
    F --> D
    D --> G[Timestamped retrieval index]
    G --> H[Quick / standard / deep analysis]
    H --> I[Follow-up Q&A]
    H --> J[Markdown / JSON / subtitles / CSV]
    B --> K{Visual information matters?}
    K -->|Yes| L[Frames and visual evidence]
    L --> H
~~~

Every stage leaves recoverable state. A bundle is marked <code>analyzed</code> only after its report, evidence, timestamps, reader, and inventory pass validation.

## Analysis modes

| Mode | Best for | Default delivery |
|---|---|---|
| <code>quick</code> | Triage and previews | Episode card, short summary, key moments, limitations |
| <code>standard</code> | Ordinary analysis requests | Chapters, claims, disagreements, actions, evidence |
| <code>deep</code> | Research, fact-checking, comparison | Argument map, claim ledger, visual evidence, verification queue |

## Sources

| Source | Strategy |
|---|---|
| YouTube | Public captions first, audio transcription fallback |
| Bilibili | Captions first; public API fallback after HTTP 412; multi-part and duration-safe acquisition |
| RSS / Atom | Precise episode selection and Podcasting 2.0 transcript discovery |
| Episode pages | JSON-LD, official transcript, RSS discovery, and <code>og:audio</code> |
| Direct media | Bounded atomic download and source fingerprint |
| Local media | Direct processing without duplicating large files |
| SRT, VTT, ASS, TTML, LRC, JSON3, JSON, TXT, MD | Normalize, index, and analyze |

> [!IMPORTANT]
> Spotify, paywalled or authenticated content, private feeds, DRM, and regional restrictions are limited to publicly available information. Podcast Reader does not bypass access controls or read browser cookies by default.

## Files and data structure

<details open>
<summary><strong>Core artifacts</strong></summary>

~~~text
episode/
├── bundle.json                   # State, provenance, inventory, warnings
├── source.json                   # Stable source metadata
├── transcript-raw.*              # Untouched source or generated transcript
├── transcript.json               # Normalized segment data
├── transcript.md                 # Readable timestamped transcript
├── transcript.srt / .vtt         # Subtitle exports
├── chunks.json                   # Follow-up retrieval index
├── transcript-quality.json       # QA metrics and review targets
├── analysis.md                   # Deep report
├── summary.md                    # Standalone summary
├── evidence.json                 # Chapters, claims, quotes, actions, entities
├── reader.html                   # Search and source-time navigation
├── *.csv                         # Optional tabular exports
└── frames/                       # Optional visual evidence
~~~

</details>

## Why the answers are easier to trust

- **Answers point somewhere:** major conclusions are tied to the smallest useful source-time window.
- **Quotes are checkable:** short quotations must occur verbatim in the referenced transcript segments.
- **Different kinds of evidence stay separate:** episode claims, Agent analysis, visual observations, and external verification are labeled distinctly.
- **Limitations are visible:** incomplete sources, weak transcription, and unanswered questions are reported directly.

The engineering guardrails below protect that experience:

| Failure mode | Guardrail |
|---|---|
| Long download ends early | Resumable ranges plus byte-count and duration validation |
| Partial cache looks complete | Source fingerprints, settings, sequence, and duration coverage |
| ASR repetition hallucination | Exact, token, and CJK within-segment pattern checks |
| Fabricated quote | Quote text must exist verbatim in referenced segments |
| Analysis reports false success | Report, evidence, reader, and bundle finalization gates |
| Export leaks local details | Absolute paths and sensitive query parameters are sanitized |
| Full transcript is shared accidentally | Share profile excludes it by default |
| Prompt injection in source media | Pages, captions, transcripts, and frames are untrusted content |

## Verified on real long-form media

The latest 98-minute Bilibili forward test completed with **no browser cookies and no cloud transcription API key**:

| Complete media | Timestamped segments | Deep chapters | Grounded claims | Automated tests |
|---:|---:|---:|---:|---:|
| 5,899.52 seconds | 202 | 9 | 11 | 58 / 58 |

The run covered resumable acquisition, four local transcription chunks, deep analysis, a searchable reader, and a privacy-safe archive. Transcript QA detected CJK within-segment repetition hallucinations and prevented them from being presented as reliable quotes.

See [forward-test results](docs/smoke-results.md) and the [delivery report](PROJECT-REPORT.md).

## Runtime

- Python 3.10+
- FFmpeg / ffprobe for media preparation and frames
- yt-dlp for public platform sources; <code>uv</code> can run the pinned version ephemerally
- Host-native transcription or local <code>faster-whisper</code> when no public transcript exists

Normalization, indexing, retrieval, RSS/page parsing, validation, and CSV export use only the Python standard library. The first local transcription run downloads isolated dependencies and model weights; long media consumes local compute and storage.

## Engineering quality

- **58 / 58** offline unit, contract, security, recovery, and end-to-end tests.
- **31** independently callable Python CLIs.
- Windows and Linux CI across Python 3.11, 3.12, and 3.14.
- Automated CLI help, Skill metadata, internal-link, and release-invariant checks.
- Deterministic release ZIP, SHA-256 sidecar, and CycloneDX SBOM.
- Real forward tests for YouTube, Bilibili, RSS, local files, and video frames.

~~~bash
python -m unittest discover -s podcast-reader/tests -v
python -m compileall -q podcast-reader/scripts
python podcast-reader/scripts/release_check.py
~~~

## Documentation

| Topic | Document |
|---|---|
| Documentation map | [Docs home](docs/README.md) |
| Architecture | [Architecture](docs/architecture.md) |
| Product benchmark | [Benchmark](docs/benchmark.md) |
| Acceptance criteria | [Quality and acceptance](docs/quality-and-acceptance.md) |
| Real platform results | [Smoke results](docs/smoke-results.md) |
| Current release | [v2.0.1 release notes](docs/release-v2.0.1.md) |
| Contribution and security | [CONTRIBUTING](CONTRIBUTING.md) · [SECURITY](SECURITY.md) |

## Security, privacy, and copyright

Podcast Reader never persists temporary signed media URLs, does not ask users to paste secrets into chat, treats source content as untrusted, and separates “what the episode says” from external verification for high-stakes claims. Privacy-safe exports omit full transcripts by default.

Read the [Security Policy](SECURITY.md) before reporting a vulnerability.

## Contributing

Source adapters, transcript formats, language fixtures, analysis workflows, and real failure cases are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## License

[MIT License](LICENSE) © 2026 Podcast Reader contributors

---

<div align="center">

If Podcast Reader helps you understand an episode faster or recover a moment you thought you had lost, consider giving the project a ⭐

[Download latest](https://github.com/Fangx-AI/podcast-reader/releases/latest) · [Open an issue](https://github.com/Fangx-AI/podcast-reader/issues) · [Back to top](#podcast-reader-v201)

</div>
