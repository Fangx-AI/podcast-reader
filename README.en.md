# Podcast Reader v1.4.0

Podcast Reader turns a public podcast or long-video link into a reusable, timestamp-grounded research bundle.

It supports Bilibili, YouTube, RSS/Atom, episode pages, direct media URLs, and local media/transcript files. Bilibili HTTP 412 responses degrade to public metadata, subtitle, and multi-part audio APIs without browser cookies. Transcription is provider-neutral: use a host Agent's native capability first, zero-key local `faster-whisper` second, and an already-configured cloud provider only when desired.

## Quick start

Copy `podcast-reader/` into a Skills directory discovered by your Agent. For Codex:

```text
~/.codex/skills/podcast-reader/
```

For clients following the portable Agent Skills convention, a common project location is:

```text
.agents/skills/podcast-reader/
```

Then ask:

```text
Use $podcast-reader to deeply analyze this link, answer with timestamp evidence, and export Markdown: https://...
```

The default workflow is:

```text
link/file → resolve → acquire → transcribe → normalize → index → analyze → ask → export
```

No API key is required for the core workflow. When the host has no native transcription tool, local mode can bootstrap a pinned `faster-whisper` environment through `uv`; the first run downloads model weights and long media consumes local compute.

Check a new machine without network access, then run the complete zero-key preparation pipeline with one command:

```text
python podcast-reader/scripts/doctor.py --json
python podcast-reader/scripts/process_episode.py <url-or-file>
```

The unified entrypoint prefers public transcripts, acquires media only when needed, resumes completed chunks, emits visible stage progress, and produces a timestamped transcript plus retrieval index.

The user-facing Chinese documentation in [README.md](README.md) contains the complete feature matrix, CLI examples, architecture, output bundle, quality policy, and safety model. See [docs/architecture.md](docs/architecture.md), [docs/quality-and-acceptance.md](docs/quality-and-acceptance.md), and [podcast-reader/references/portability.md](podcast-reader/references/portability.md) for engineering details.

## Development

```text
python -m unittest discover -s podcast-reader/tests -v
python -m compileall -q podcast-reader/scripts
```

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) first.

## License

MIT License. See [LICENSE](LICENSE).
