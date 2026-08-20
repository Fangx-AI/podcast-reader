# Visual evidence lane

Use this lane for video sources only when frames can change the answer.

## Trigger conditions

Inspect video frames when the source contains or may contain:

- slides, charts, tables, diagrams, or citations;
- screen recordings, code, product demonstrations, or tutorials;
- on-screen comments, captions, labels, dates, or corrections;
- physical demonstrations or objects referenced vaguely in speech;
- editing, body language, composition, or visual rhetoric requested by the user.

Skip it for audio-only sources and static talking-head footage when the user's question is fully answered by speech.

## Sampling workflow

```text
python "{skill_dir}/scripts/extract_keyframes.py" <local-video> --output-dir <episode_dir>/frames
```

The default interval strategy produces a bounded overview. Use scene sampling for slide-heavy or edited videos:

```text
python "{skill_dir}/scripts/extract_keyframes.py" <local-video> --output-dir <episode_dir>/frames --strategy scene --max-frames 24
```

First inspect `contact-sheet.jpg`. Open full-size frames only around relevant timestamps. If a transcript chapter is important, optionally extract an additional exact frame with FFmpeg instead of increasing the entire sample count.

## Evidence separation

Record frame observations as `visual evidence [HH:MM:SS]`. Do not attribute text visible on a slide to a speaker unless they also say it. Do not treat a chart as verified data merely because it appears on screen.

For each material observation capture:

| Field | Meaning |
|---|---|
| Timestamp | Video time of frame |
| Observation | Literal visible content |
| Interpretation | Analyst inference, if any |
| Relevance | Which chapter/claim it supports or complicates |
| Confidence | High/medium/low based on legibility and sampling |

OCR can misread stylized fonts, low-resolution text, numbers, and mixed scripts. Verify important text against a nearby frame or source link. A sampled-frame lane cannot prove that an unobserved event never occurred; state this limitation for exhaustive visual questions.
