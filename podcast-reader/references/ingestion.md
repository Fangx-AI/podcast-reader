# Ingestion operations

The acquisition layer is public, subtitle-first, cache-aware, and explicit about partial results.

## One-command path

```text
python "{skill_dir}/scripts/prepare_episode.py" <url-or-path> --output-root outputs/podcast-reader
```

Useful controls:

```text
# Metadata and captions only; never download audio
python "{skill_dir}/scripts/prepare_episode.py" <url> --mode subtitles

# Force a fresh metadata/acquisition pass
python "{skill_dir}/scripts/prepare_episode.py" <url> --refresh

# Select a feed item
python "{skill_dir}/scripts/prepare_episode.py" <feed> --query "episode title"

# Process the newest feed item only when explicitly requested
python "{skill_dir}/scripts/prepare_episode.py" <feed> --latest

# Resume the same bundle after an external transcription finishes
python "{skill_dir}/scripts/prepare_episode.py" <original-source> --output-dir <episode_dir> --transcript <generated-transcript>
```

## Platform adapter

`scripts/ingest_media.py` wraps `yt-dlp` with `--ignore-config`, `--no-playlist`, no implicit cookies, bounded automatic audio duration, and compact metadata that omits temporary signed format URLs.

| Mode | Behavior |
|---|---|
| `auto` | Metadata → captions → audio only if captions are absent |
| `metadata` | Metadata only |
| `subtitles` | Metadata and human/automatic captions; no audio |
| `audio` | Metadata and audio |
| `video` | Metadata and a bounded public video copy (up to 720p) for visual evidence |
| `all` | Metadata, captions, and audio |

For RSS, episode pages, and direct media, `metadata` and `subtitles` modes never fall back to downloading audio. `auto` downloads audio only when no public transcript is available. Cache reuse is mode- and language-aware; a metadata preview cannot block a later full run.

```text
python "{skill_dir}/scripts/ingest_media.py" <url> --output-dir <episode_dir> --mode auto
```

Language order can be changed with `--sub-langs`. Keep every downloaded language track; choose one for normalization without deleting the others.

## Bilibili

1. Resolve `b23.tv` redirects through public metadata.
2. Request public subtitle tracks, including automatic tracks when available.
3. If `yt-dlp` receives HTTP 412, use the public web APIs for metadata, subtitle discovery, and public playback streams; do not use browser cookies implicitly.
4. If no caption file is acquired, normalize every public multi-part audio stream separately and transcribe the parts in order.
5. Treat subtitle timing, names, and speaker attribution as medium confidence until checked.
6. Preserve every part as an ordered media artifact in one episode bundle so follow-up transcription cannot silently omit later parts.

### Explicit Agent-Reach / bili-cli audio adapter

When the caller explicitly chooses an already installed Agent-Reach/bilibili-cli environment, use `scripts/ingest_bilibili_cli.py`. This is a separate audio-acquisition adapter; `prepare_episode.py` and `process_episode.py` do not select it automatically. It does not install or upgrade packages, discover browser cookies, load a bili-cli login profile, or fall back to authenticated access.

Run it with the Python interpreter that already has `bili_cli` installed. A missing backend produces a structured dependency failure rather than an installation attempt. `--help` works without that optional package.

```text
# Inspect public metadata and available parts; no audio download
"<bili-cli-python>" "{skill_dir}/scripts/ingest_bilibili_cli.py" <BV-id-or-canonical-URL> --output-dir outputs/bili-cli-inspect --mode metadata

# Acquire a single-part video, or explicitly select one part
"<bili-cli-python>" "{skill_dir}/scripts/ingest_bilibili_cli.py" "https://www.bilibili.com/video/<BV-id>/?p=2" --output-dir outputs/bili-cli-p2 --mode audio --max-duration-minutes 480
```

The adapter accepts a BV ID or a canonical `bilibili.com/video/BV...` URL. Short links and av IDs must first be resolved to a canonical BV URL. Multi-part videos require `--page N` or URL `?p=N`; without a selection the result is `needs_selection` and no audio is downloaded. Conflicting selections fail. It processes **one selected part per invocation**; use separate output directories for different parts. It does not treat an acquired part as a complete multi-part episode.

Backend behavior was checked against bilibili-cli 0.6.2 and its installed bilibili-api-python 17.4.2 dependency. In that version, `get_audio_url` always selects P1. For an explicitly selected later part, this adapter uses the same installed SDK with the selected CID and the same 64K audio-selection policy. Every metadata/stream call or video constructor receives `credential=None` explicitly. A platform denial remains a failure; this path does not bypass access controls.

The default upper bound is **480 minutes for the selected part**, matching the existing platform adapter. A positive metadata duration is required before download and for completeness checks. `--max-duration-minutes 0` explicitly disables only the upper limit; it does not permit an unknown duration. `--max-bytes` defaults to 2 GiB. FFmpeg and ffprobe must already be available: the helper checks source duration, copies only the audio track into M4A, verifies its duration again, then publishes it atomically. A failed refresh preserves an existing file but is not reported as successful. Valid cached audio for the same BV, part and CID can be reused.

The stream URL exists only in memory. The helper uses the existing bounded range downloader, saves allowlisted source metadata, redacts remote URLs from failures, and suppresses third-party lookup output. Durable artifacts are `source.json`, `source-info.json`, audio, and `ingest-result.json`. `source.json` includes `kind=remote_media` and the publication date in UTC `YYYYMMDD` format when valid metadata supplies it. The result has the same `status`, `transcript_status`, `source`, `files`, `warnings`, and `next_actions` fields consumed by the existing preparation layer; `files.media` and `files.audio` contain only the selected, verified file. Successful audio acquisition is `ready` / `needs_transcription`, not a finished summary. Exit code is 0 for `ready` or `metadata_only`, and 2 for selection, partial, or blocked states.

After transcribing the selected audio, reuse the normal attachment path with the canonical URL from `source.canonical_url` and the same directory. This preserves source provenance and includes the acquired audio in the bundle inventory without another media acquisition:

```text
python "{skill_dir}/scripts/prepare_episode.py" "<canonical-URL-including-selected-p>" --output-dir <same-directory> --transcript <completed-transcript>
python "{skill_dir}/scripts/create_analysis_contract.py" <same-directory> --mode summary --output-language <user-language>
```

The adapter's own offline tests cover anonymous credentials, selection and duration limits, successful attachment through `prepare_episode.py`, cache integrity, and URL privacy. They do not establish that every public Bilibili video is accessible.

## YouTube

Use an available purpose-built YouTube transcript skill when it provides stronger chapters/speaker metadata; otherwise the same `yt-dlp` subtitle-first adapter is sufficient. Prefer creator captions over auto captions when both are available. Do not assume auto-translated captions equal the source transcript.

## Direct media

`scripts/fetch_audio.py` enforces HTTP(S), a maximum size, `.part` cleanup, atomic completion, deterministic naming, and SHA-256 recording. It is for direct downloadable media, not HTML player pages.

## Dependencies

- Python 3.10+.
- `yt-dlp`, or `uv` so the adapter can run the release-pinned yt-dlp version ephemerally without changing global packages.
- FFmpeg/ffprobe for audio extraction, conversion, and visual sampling.
- A transcription provider only when no transcript/caption exists.

Before cloud transcription, compare every media artifact with the provider's upload limit. Use `prepare_audio_chunks.py` for oversized or multi-part audio, transcribe the emitted `.ogg` files in manifest order with a timestamped response format, and use `combine_chunk_transcripts.py` to restore the episode-global timeline.

Dependency failures must name the exact missing component and stage. Do not silently switch to an unrelated downloader.

## Cookies and restricted content

Do not use browser cookies by default. `--cookies-from-browser` exists only for an explicitly approved, lawful, local attempt. Never bypass DRM, payment, login, region, private-feed, anti-bot, or platform access controls. Ask for a user-provided transcript, subtitle, or authorized local media export when blocked.

## Cache and idempotency

- `bundle.json` is the cache marker.
- The bundle records request mode/language and is reused only when existing artifacts satisfy the new request.
- Existing acquired files are not overwritten unless `--force`/`--refresh` is used.
- Raw captions/media remain immutable inputs.
- Regenerate derived transcript/index/report files only when source input or relevant settings changed.
- A partial bundle remains reusable; continue from its `next_actions` rather than restarting.
- Persisted provenance strips credentials and temporary/tracking query parameters from media URLs while runtime acquisition still uses the original address.
