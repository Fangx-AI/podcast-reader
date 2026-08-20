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

## YouTube

Use an available purpose-built YouTube transcript skill when it provides stronger chapters/speaker metadata; otherwise the same `yt-dlp` subtitle-first adapter is sufficient. Prefer creator captions over auto captions when both are available. Do not assume auto-translated captions equal the source transcript.

## Direct media

`scripts/fetch_audio.py` enforces HTTP(S), a maximum size, `.part` cleanup, atomic completion, deterministic naming, and SHA-256 recording. It is for direct downloadable media, not HTML player pages.

## Dependencies

- Python 3.10+.
- `yt-dlp`, or `uv` so the adapter can run yt-dlp ephemerally.
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
