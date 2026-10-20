# Summary workflow

The default task is a concise, evidence-backed podcast summary that takes approximately 3–5 minutes to read. The core editorial job is to **identify key questions and high-value information**, not to shorten every section equally.

## 1. Establish coverage

Read source metadata, the transcript quality report, and the full chunk inventory. Inspect the transcript in bounded batches across every substantive part of the episode. Track its central question, major turns, conclusions, disagreements, and exceptions.

A keyword search is useful for verification after broad reading; a few top-ranked hits are not sufficient evidence for a whole-episode summary. Check neighboring chunks when a speaker qualifies a point or responds to someone else. Do not erase a later correction because an earlier statement is easier to summarize.

If the source is partial, summarize only the available content and explicitly state the scope. Metadata-only preparation cannot produce an episode summary.

## 2. Find the questions a listener cares about

A key question should make the reader want its answer because it clarifies the episode's stakes. Typical forms include:

- What decision is being discussed, and what changes the answer?
- Why does the speaker think a common assumption is wrong?
- How does the proposed method actually work?
- What evidence or example changes the conclusion?
- Where does the advice stop applying, or where do speakers disagree?
- For narrative material: what happened, why did it happen, and what changed?

These are editorial prompts, not required categories. Write questions specific to the episode. Avoid generic prompts such as “What is the topic?” or “What did the guest say?” when a concrete question is available.

Each `quick_takes` item needs:

1. A clear question.
2. A direct answer in its first sentence.
3. Enough reasoning, an example, or a caveat to make the answer useful.
4. Source references covering all material parts of the answer.

Usually select 3–6 questions. Short sources may support only one or two.

## 3. Rank the information worth keeping

Select 3–7 high-value insights when the source supports them. Use fewer when it does not. Prefer items with clear relevance, specificity, evidence, and explanatory value.

| Optional kind | What earns a place | Preserve |
|---|---|---|
| `decision` | A conclusion that could change an assessment or decision | Who it applies to, conditions, tradeoffs |
| `counterintuitive` | A credible challenge to a common assumption | What changed and the speaker's reasoning |
| `data` | A revealing number, experiment, or concrete case | Context, units, scope, and whether it is anecdotal |
| `method` | A usable process or mechanism | Actual steps, prerequisites, limits |
| `pitfall` | An important failure mode, risk, or boundary | Why it fails and when the warning matters |
| `insight` | Another central idea, narrative development, or meaningful disagreement | Explanation and source context |

Kinds are optional labels, not six mandatory boxes. If a speaker supplies no numbers or methods, do not invent them. An anecdote can be memorable without proving a general claim. Explain why an insight matters through its substance rather than adding a generic “this is important” sentence.

Remove repetition across quick answers and insights. An insight can deepen a short answer with its mechanism, example, or limit; it should not repeat it verbatim.

## 4. Preserve meaning while compressing

- Put the central question and takeaway at the top.
- Retain the strongest qualifying condition, meaningful disagreement, or exception.
- Attribute opinions, predictions, and recommendations to the speaker. Label a cross-passage inference as a synthesis.
- Keep names, figures, dates, and units exact when confirmed; otherwise omit or qualify them.
- Introduce participants only when source metadata or introductions establish their identity. Do not guess credentials or biographies.
- Include up to three short exact quotes only when their wording adds value.
- Include optional `open_questions` only for questions genuinely raised but left unresolved in the episode. They are not the Agent's speculative list of future research topics.
- Do not force action advice onto stories, fiction, comedy, history, or cultural discussions.
- Write in the user's language. Preserve original technical terms when translation would obscure meaning.

A 3–5 minute reading target is an editorial target, not a guarantee based on runtime or word count. Do not fill available space just because the validator allows it.

## 5. Evidence and completion

Write `evidence.json` using the [output contract](output-schema.md). Reference source segments for the takeaway, each quick answer, and each insight. Cite all distant passages used in a synthesis. Time ranges must come from the actual transcript; untimed sources use segment IDs without fabricated times.

Run `finalize_bundle.py`, then `validate_bundle.py`. In `summary` mode, finalization generates `summary.md`, a compatibility `analysis.md`, and `reader.html` from the same validated evidence. Deliver the first and last of these with clickable links.

Check the result as a reader:

- Can I identify the episode's central question within a few seconds?
- Do the questions express real stakes and give direct answers?
- Does each insight contain something specific worth retaining?
- Are reasoning, boundaries, and disagreements preserved where they change meaning?
- Does the result cover the episode rather than just an opening segment or search result?
- Can each main point be checked against its source?
- Can I finish the summary in a few minutes without reading processing details?

`ready_for_analysis` means the source is ready. Only successful finalization and validation justify calling the summary complete.

## Legacy compatibility

`quick`, `standard`, and `deep` are retained for callers that explicitly request the old contracts. They are not recommended alternatives for a normal podcast-summary request. Existing report integrations can keep their original `analysis.md`, claim ledger, and evidence structures; the default product follows the workflow above.
