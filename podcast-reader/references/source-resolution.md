# Source resolution contract

Use this reference when an input is a feed, episode webpage, redirect, direct media URL, or ambiguous local file.

## Classification table

| Input | Preferred path | Content confidence |
|---|---|---|
| User/publisher transcript | Normalize directly | High, subject to source quality |
| Local audio/video | Transcribe; diarize conversations | Medium–high |
| YouTube/Bilibili | Public captions first, audio second | Medium–high |
| RSS/Atom | Select item, use transcript link or enclosure | Metadata high; content depends on artifact |
| Episode webpage | Official transcript, feed link, audio metadata | Variable |
| Direct media URL | Bounded atomic download, then transcribe | Medium–high |
| Login/paywall/private feed | Public metadata only | Partial |

Run the resolver independently when diagnosing:

```text
python "{skill_dir}/scripts/resolve_podcast.py" <input>
python "{skill_dir}/scripts/resolve_podcast.py" <feed> --query "exact episode title"
python "{skill_dir}/scripts/resolve_podcast.py" <feed> --latest
python "{skill_dir}/scripts/resolve_podcast.py" <url> --no-network
```

## Feed selection

Match in this order:

1. Explicit episode URL or GUID.
2. Exact title.
3. Unique case-insensitive title substring.
4. Newest parseable publication date when the user explicitly says “latest” or passes `--latest`; fall back to the first item only when feed dates are unavailable.

If multiple candidates remain, return `needs_selection` with a short candidate list. Never silently choose by list position when the user named an episode.

Podcasting 2.0 transcript links are preferred over audio transcription when public and readable. Keep feed descriptions/show notes as metadata; they are not a substitute for dialogue.

## Webpage rules

Inspect, in order:

1. JSON-LD `PodcastEpisode`, `AudioObject`, or `VideoObject`.
2. Official transcript links.
3. RSS/Atom discovery links.
4. `og:audio`, `twitter:player:stream`, `<audio>`, and media `<source>`.

Treat each media URL as a candidate until its title/context is consistent with the requested episode. A search result snippet or page description is never a transcript.

## Canonical identity and refresh

The bundle ID is derived from a normalized URL or local path plus file size/mtime. Reuse a matching bundle unless the user asks to refresh, the source changed, or required artifacts fail validation. Redirected URLs should be recorded separately as requested and canonical URLs.
