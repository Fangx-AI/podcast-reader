# Changelog

All notable changes to this project are documented here.

## 2.0.0 — 2026-08-20

### Reliability and security

- Verify chunk caches with source SHA-256 fingerprints, settings, contiguous indexes, and full-duration coverage; rebuild incomplete caches transactionally.
- Validate local transcript caches against source and decoding settings; quarantine corrupt/legacy partial files and write all durable JSON atomically.
- Return an action-required exit code for selection/partial states instead of false success.
- Distinguish installed, bootstrap-capable, and offline-ready capabilities in Doctor; test real output writes and report free disk space.
- Reject loopback, private, link-local, reserved, credential-bearing, and unsafe redirect targets by default.

### Evidence and user experience

- Require `analysis.md` plus schema-validated `evidence.json` before `analyzed`; verify enums, segment references, timestamp ranges, chapter order, and exact quotes.
- Add a provider-neutral Agent analysis handoff, transcript quality assessment, per-chunk percentage/ETA, partial transcript publication, and overlapped speech chunks.
- Add arbitrary target-language translation requests/application, provider-neutral diarization turns, compact budgeted retrieval, and retrieval confidence.
- Generate an accessible searchable `reader.html` with platform timestamp links.
- Add privacy-sanitized share/portable/archive exports and preview-first cache/media cleanup.

### Release engineering

- Add single-source `VERSION`, downgrade protection, backup listing/pruning/rollback, release invariant checks, CycloneDX SBOM generation, deterministic ZIPs, and SHA-256 sidecars.
- Expand regression coverage for every confirmed v1.4 audit defect and pin GitHub Actions by commit.

## 1.4.0 — 2026-08-20

### Added

- `process_episode.py`, a unified zero-key entrypoint for resolve → acquire → resumable chunking → local transcription → global timeline → searchable bundle.
- `doctor.py`, an offline environment check for Python, output permissions, FFmpeg, yt-dlp/uv, and local transcription readiness.
- `install_skill.py`, a cross-platform installer with collision refusal and recoverable forced updates.
- Durable `progress.json` stage events and visible terminal updates for long-running work.
- Product tests for the unified entrypoint and machine-readable zero-key diagnostics.
- Evidence-aware cross-language retrieval: bilingual glossary expansion and translated claim/action/entity routing back to source segment IDs.

### Fixed

- Transcript attachment now reuses an existing bundle's source resolution instead of depending on a second network lookup.
- Pipeline failures are recorded as explicit failed progress events when an episode directory is available.

### Changed

- Expand CI to Windows/Linux across Python 3.11, 3.12, and 3.14.
- Make the unified entrypoint the default documented path while retaining lower-level helpers for host-native providers and diagnostics.

## 1.3.1 — 2026-08-19

### Fixed

- Add an explicit analysis finalization gate so completed bundles no longer remain mislabeled `ready_for_analysis`.
- Strictly validate `analysis.md`, optional `summary.md`, and every `evidence.json` segment reference before changing bundle state to `analyzed`.
- Refresh the artifact inventory and replace stale “analyze transcript” next actions after successful finalization.

### Changed

- Recommend resumable batched local transcription (`--beam-size 1 --batch-size 4`) for practical multi-hour CPU runs.

## 1.3.0 — 2026-08-19

### Changed

- Make transcription provider-neutral: host-native capability first, local zero-key fallback second, configured cloud providers optional.
- Remove the OpenAI API Key assumption from the default workflow and documentation.
- Declare portable Agent Skills compatibility and runtime requirements in frontmatter.

### Added

- `transcribe_local.py`, a pinned `faster-whisper` adapter with isolated `uv` bootstrap, CPU/GPU selection, multilingual timestamps, VAD, and JSON output.
- Cross-Agent portability and transcription-provider contract documentation.
- Automatic spoken-language detection for Bilibili instead of inferring language from the platform or title.
- Resumable local chunk transcription plus batched-inference controls for practical multi-hour CPU runs.

## 1.2.0 — 2026-08-19

### Fixed

- Fall back to Bilibili's public play API when extractor requests receive HTTP 412.
- Acquire every public multi-part audio stream without browser cookies and normalize each part with FFmpeg.
- Keep temporary signed CDN URLs out of durable metadata and diagnostics.
- Distinguish a publisher with no public subtitle track from a failed subtitle request.

### Added

- Regression coverage for multi-part Bilibili audio fallback and private play-context redaction.
- API-safe Opus chunk preparation with ordered source/global offsets.
- Timestamp-preserving recombination of diarized chunk transcripts.

## 1.1.0 — 2026-08-19

### Fixed

- Resolve skill helper paths from `{skill_dir}` instead of assuming the current working directory.
- Prevent RSS, episode-page, and direct-media `metadata`/`subtitles` modes from downloading audio.
- Make bundle cache reuse aware of mode, language, and available artifacts.
- Add `--transcript` to resume a media bundle after external transcription.
- Split oversized single-segment transcripts into bounded retrieval chunks.
- Select RSS `--latest` by publication date rather than document order.
- Reject non-media direct-download responses, avoid filename collisions, and redact persisted signed/tracking URLs.
- Require source provenance in bundles and strict Markdown reports.

### Added

- Explicit bounded 720p `video` acquisition mode for visual evidence.
- ASS, TTML, LRC, and YouTube JSON3 transcript compatibility.
- Structured timeout degradation and rolling-caption deduplication.
- Branded Codex UI icons and accent color.
- 24-scenario release audit across Python 3.11, 3.12, and 3.14.

## 1.0.0 — 2026-08-19

### Added

- Link-first podcast and long-video workflow for Bilibili, YouTube, RSS/Atom, episode pages, direct media, and local files.
- Subtitle-first yt-dlp adapter with uv fallback, compact metadata, explicit cookie policy, and graceful partial results.
- Bilibili public metadata/subtitle fallback for extractor-side HTTP 412 failures.
- One-command reusable episode bundles with cache identity, artifact inventory, warnings, and next actions.
- SRT, VTT, JSON, TXT, and Markdown transcript normalization with timestamp and speaker preservation.
- Multilingual dependency-free chunk retrieval and persistent follow-up Q&A workflow.
- FFmpeg interval/scene keyframes, contact sheet, and visual evidence manifest.
- Quick, standard, and deep analysis modes plus claim, speaker, translation, study, repurpose, fact-check, compare, and visual workflows.
- Polished Chinese report template and Markdown/JSON/SRT/VTT/CSV export contracts.
- Bundle/report validators, offline fixtures, golden output, CLI contract tests, and public smoke-test specification.
- Security, privacy, copyright, contribution, architecture, and acceptance documentation.
