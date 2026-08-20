# Portability and transcription providers

Podcast Reader follows the portable Agent Skills directory format. The workflow is provider-neutral; platform clients decide how `SKILL.md` is discovered and which tools are available.

## Capability ladder

| Priority | Capability | Secret required | Main trade-off |
|---|---|---:|---|
| 1 | Host Agent's native timestamped transcription | Usually no new secret | Availability and output schema vary by client |
| 2 | Bundled local `faster-whisper` adapter | No | First-run model download; CPU/GPU time; no built-in diarization |
| 3 | User-configured cloud/CLI/MCP provider | Provider-dependent | Cost, privacy, account, and upload limits |
| 4 | User-provided transcript/subtitles | No | Depends on source availability |

Never make OpenAI, Anthropic, Google, or another vendor credential a hard dependency of the core skill.

## Zero-key local mode

The portable one-command path is:

```text
python "{skill_dir}/scripts/process_episode.py" <url-or-file> --output-root outputs/podcast-reader
```

It uses the local adapter only when a public transcript is unavailable. Agents with a better native timestamped transcription capability may stop after acquisition and attach their own compliant JSON instead.

`doctor.py` distinguishes `offline_ready` (dependencies already installed) from `bootstrap_ready` (the first run still needs network and downloads). Do not describe bootstrap capability as installed readiness.

`scripts/transcribe_local.py` writes timestamped JSON compatible with the normalizer and chunk-combiner. It pins `faster-whisper==1.2.1` for repeatability.

```text
python "{skill_dir}/scripts/transcribe_local.py" <audio-or-chunks...> --output-dir <transcript-dir> --bootstrap --model small --language auto --beam-size 1 --batch-size 4
```

`--bootstrap` requires `uv`; it creates an ephemeral Python 3.12 dependency environment rather than modifying the user's global Python installation. The Whisper model is downloaded and cached on first use. CPU mode uses int8; compatible CUDA environments use float16 automatically and fall back to CPU if automatic GPU initialization fails.

Recommended profiles:

| Profile | Model | Use |
|---|---|---|
| Smoke | `tiny` | Verify installation and routing only |
| Standard | `small` | Default multilingual podcast analysis |
| Quality | `large-v3` | Stronger accuracy when hardware/time permits |

Local mode does not identify speakers. Preserve `speaker: null` or generic unknown labels. If speaker-aware analysis matters, prefer a host/provider with diarization or add a separately validated diarization lane.

Per-chunk transcript files are reused only after source fingerprints, decoding settings, JSON structure, and completion state match. Audio chunks overlap briefly at speech boundaries and are accepted only when ordered time ranges cover the full source. `--batch-size 4` is the long-form CPU starting point; reduce it on memory-constrained machines.

## Cross-Agent behavior

From a cloned or extracted repository, install into Codex's default Skills directory with:

```text
python podcast-reader/scripts/install_skill.py --json
```

Pass `--target <skills-directory>` for another Agent. The installer refuses to overwrite an existing skill unless `--force` is explicit; forced updates preserve the previous directory as a timestamped sibling backup.

- If the client supports Agent Skills and shell execution, it can run the bundled Python scripts.
- If the client supports Agent Skills but no shell, it must supply equivalent native media/transcription tools.
- If the client supports neither scripts nor audio tools, the skill can still analyze user-provided transcripts but cannot manufacture a transcription capability.
- Client-specific metadata such as `agents/openai.yaml` is optional decoration; the portable contract remains `SKILL.md`, `scripts/`, `references/`, and `assets/`.

## Provider output contract

Any transcription adapter is acceptable when it produces UTF-8 JSON containing a `segments` list. Each segment should include `text`, numeric `start`/`end` (or `start_seconds`/`end_seconds`), and optional `speaker`, `language`, and `confidence`. Keep raw provider output separate from normalized artifacts.
