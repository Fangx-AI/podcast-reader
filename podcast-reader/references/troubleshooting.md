# Troubleshooting and fallback matrix

Return available artifacts plus a precise stage and next action. Do not collapse partial work into a generic failure.

| Stage | Symptom | Safe response |
|---|---|---|
| Resolve | Unknown URL/page | Inspect public metadata; request direct feed/media/transcript |
| Feed select | Multiple matches | Show candidates; require exact title/GUID |
| Metadata | yt-dlp extractor error | Update yt-dlp; verify public URL; do not bypass restriction |
| Subtitle | No track acquired | Continue to public audio extraction/transcription |
| Audio | FFmpeg missing | Report dependency and preserve metadata/captions |
| Download | Size/timeout/empty file | Keep no partial file; ask for local export or raise explicit limit |
| Access | Login/region/paywall/DRM | Stop; request authorized local media/transcript |
| Transcription | Provider/key/format failure | Explain local configuration; convert audio with FFmpeg if format-only |
| Diarization | Unstable speakers | Use unknown speaker labels; reduce attribution confidence |
| Normalize | No segments parsed | Keep raw file; inspect encoding/format; convert to SRT/VTT/JSON |
| Index | Empty chunks | Validate transcript segments before rerun |
| Visual | FFmpeg/scene extraction fails | Fall back to interval frames or transcript-only analysis |
| Analysis | Insufficient evidence | Return bounded partial answer and identify missing evidence |
| Export | Validator failure | Fix missing section/timestamp/placeholders before delivery |

## Dependency checks

```text
python "{skill_dir}/scripts/doctor.py" --json
```

The doctor is the preferred first check: it performs no downloads or network requests and reports which workflows are ready, degraded, or blocked. Use individual commands only when diagnosing one binary:

```text
python --version
ffmpeg -version
ffprobe -version
yt-dlp --version
uv run --with yt-dlp yt-dlp --version
```

The adapter uses installed `yt-dlp` first, then an ephemeral `uv` copy. Updating the extractor is often the correct first step when a public platform changes.

## Common statuses

- `ready_for_analysis` — transcript and index exist.
- `needs_transcription` — media exists, but no normalized transcript.
- `needs_selection` — source is valid but episode/media selection is ambiguous.
- `metadata_only` — metadata was requested or content acquisition was intentionally skipped.
- `partial` — some useful artifacts exist; read warnings/next actions.
- `blocked` — no safe path can continue without a different source, authorization, or dependency.

## Recovery discipline

1. Read `bundle.json` before rerunning anything.
2. Retry only the failed stage.
3. Preserve raw acquired files.
4. Use `--refresh` only when source/platform state changed.
5. Validate the bundle after recovery.

`process_episode.py` is resumable by default. Re-run the same command after a local interruption; use `--force` only when cached chunks or transcripts are known to be wrong.
