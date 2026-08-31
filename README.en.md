# Podcast Reader v2.0.1

<div align="center">

## 🎧 Turn hours of podcasts and long-form video into searchable, verifiable knowledge

One link in. A timestamp-grounded research bundle, follow-up Q&A, and portable exports out.

[![Release](https://img.shields.io/github/v/release/Fangx-AI/podcast-reader?style=flat-square&color=2563eb)](https://github.com/Fangx-AI/podcast-reader/releases/latest)
[![CI](https://img.shields.io/github/actions/workflow/status/Fangx-AI/podcast-reader/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/Fangx-AI/podcast-reader/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/github/license/Fangx-AI/podcast-reader?style=flat-square)](LICENSE)
![API Key](https://img.shields.io/badge/Cloud_API_Key-optional-16a34a?style=flat-square)

[中文](README.md) · [English](README.en.md) · [Latest release](https://github.com/Fangx-AI/podcast-reader/releases/latest) · [Documentation](docs/README.md) · [Issues](https://github.com/Fangx-AI/podcast-reader/issues)

</div>

> [!NOTE]
> Podcast Reader is not another summarizer. It gives long-form audio and video durable text memory, timestamp evidence, structured claims, and a reusable local research bundle.

---

## At a glance

| You provide | Podcast Reader handles | You receive |
|---|---|---|
| Bilibili or YouTube URL | Source resolution, public captions, audio fallback | Searchable timestamped transcript |
| RSS feed or episode page | Episode selection and transcript discovery | Chapters and timeline |
| Local media or transcript | Local transcription, normalization, QA | Claims, quotes, and evidence |
| A natural-language question | Evidence-aware retrieval | An answer linked to source time |
| An export request | Privacy sanitization and rights-aware filtering | Markdown, JSON, SRT, VTT, CSV, HTML |

### Beyond transcription

| Capability | Typical transcription tool | Podcast Reader |
|---|:---:|:---:|
| Speech to text | ✓ | ✓ |
| Resumable long-media processing | varies | ✓ |
| Argument, disagreement, and chapter analysis | — | ✓ |
| Claims grounded to exact segments | — | ✓ |
| Process once, ask repeatedly | — | ✓ |
| Visual evidence from video | — | ✓ |
| Translation with segment mapping | — | ✓ |
| Privacy-safe share bundle | — | ✓ |
| Vendor-neutral core | — | ✓ |

## Verified on real long-form media

The latest 98-minute Bilibili forward test completed with **no browser cookies and no cloud transcription API key**:

| Complete media | Timestamped segments | Deep chapters | Grounded claims | Automated tests |
|---:|---:|---:|---:|---:|
| 5,899.52 seconds | 202 | 9 | 11 | 58 / 58 |

The run covered resumable acquisition, four local transcription chunks, deep analysis, a searchable reader, and a privacy-safe archive. Transcript QA detected two CJK within-segment repetition hallucinations and prevented them from being presented as reliable quotes.

See [forward-test results](docs/smoke-results.md) and the [delivery report](PROJECT-REPORT.md).

---

## Quick start

### 1. Clone and install

~~~bash
git clone https://github.com/Fangx-AI/podcast-reader.git
cd podcast-reader
python podcast-reader/scripts/install_skill.py --json
~~~

To update an existing installation, opt in explicitly. The installer preserves a timestamped backup first.

~~~bash
python podcast-reader/scripts/install_skill.py --force --json
~~~

You can also download the [latest release](https://github.com/Fangx-AI/podcast-reader/releases/latest) and copy its <code>podcast-reader/</code> folder into a Skills directory discovered by your Agent.

| Client | Common location |
|---|---|
| Codex | <code>~/.codex/skills/podcast-reader/</code> |
| Agent Skills-compatible clients | <code>.agents/skills/podcast-reader/</code> |

### 2. Ask naturally

~~~text
Use $podcast-reader to deeply analyze this link, ground every major claim to timestamps, and export Markdown: https://...
~~~

That is enough. Standard mode chooses a sensible workflow without starting with a technical questionnaire.

### 3. Optional machine check

~~~bash
python podcast-reader/scripts/doctor.py --json
~~~

Doctor is offline and distinguishes installed readiness from bootstrap capability. It reports whether FFmpeg, yt-dlp, local transcription, storage, or output permissions need attention.

> [!TIP]
> A cloud API key is optional. Public transcripts are preferred. When none exists, Podcast Reader can use the host Agent's native transcription capability or bootstrap an isolated local <code>faster-whisper</code> runtime through <code>uv</code>.

## Example requests

~~~text
Break down this Bilibili interview and focus on the guest's view of AI agents.

Where do the host and guest disagree? Answer only from the episode and cite timestamps.

Translate this into Chinese while preserving important English quotes, terms, and timestamps.

Export a Notion-friendly Markdown report and a CSV claim ledger.

Compare these three episodes: consensus, conflict, assumptions, and unanswered questions.

Extract charts and slides from the video and connect visual evidence to spoken claims.
~~~

Existing bundles are reused. Follow-up questions search <code>chunks.json</code> and <code>evidence.json</code> instead of downloading or transcribing the episode again.

## How it works

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

## Research bundle

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

## Reliability by design

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

If Podcast Reader helped you truly read a long-form episode, consider giving the project a ⭐

[Download latest](https://github.com/Fangx-AI/podcast-reader/releases/latest) · [Open an issue](https://github.com/Fangx-AI/podcast-reader/issues) · [Back to top](#podcast-reader-v201)

</div>
