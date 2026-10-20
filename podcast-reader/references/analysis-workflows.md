# Summary workflow

The default task is a concise, evidence-backed podcast summary that takes approximately 3–5 minutes to read. The core editorial job is to **identify key questions and high-value information**, not to shorten every section equally.

Design two reading depths. In the first 30 seconds, the title, takeaway, and first sentences of the key answers should communicate the central issue, answer, and major boundary. The insights then reward a closer read with mechanisms, examples, methods, or exceptions that were not already explained.

For a substantial episode, target approximately **900–1,600 Chinese characters or 500–900 English words** across the visible summary. These are editorial ranges, not minimums, schema limits, or a reason to pad a short episode. The renderer estimates reading time from the finished text; the target does not justify displaying a fixed reading time.

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

1. A short, concrete question with one main point.
2. A direct answer in its first sentence, understandable without reading the rest of the page.
3. Only the essential reason or caveat; reserve detailed calculations and procedures for insights.
4. Source references covering all material parts of the answer.

Usually select 3–6 questions. Short sources may support only one or two.

For Chinese, a question often fits in 6–16 characters and its answer in 30–60. Use these as editing cues, not enforced limits. Preserve a decisive condition even when it needs extra words. Rank questions by importance to the reader, not by their original timestamp. The reader should not need to read six long paragraphs before finding the central answer.

## 3. Rank the information worth keeping

Select 3–7 high-value insights when the source supports them. Use fewer when it does not. Prefer items with clear relevance, specificity, evidence, and explanatory value.

Start with a candidate list, then order it by: effect on understanding or decisions, distinctiveness, specificity, and strength of episode evidence. Remove low-value items before polishing prose. Do not make every source section equally prominent merely to demonstrate coverage.

| Optional kind | What earns a place | Preserve |
|---|---|---|
| `decision` | A conclusion that could change an assessment or decision | Who it applies to, conditions, tradeoffs |
| `counterintuitive` | A credible challenge to a common assumption | What changed and the speaker's reasoning |
| `data` | A revealing number, experiment, or concrete case | Context, units, scope, and whether it is anecdotal |
| `method` | A usable process or mechanism | Actual steps, prerequisites, limits |
| `pitfall` | An important failure mode, risk, or boundary | Why it fails and when the warning matters |
| `insight` | Another central idea, narrative development, or meaningful disagreement | Explanation and source context |

Kinds are optional labels, not six mandatory boxes. If a speaker supplies no numbers or methods, do not invent them. An anecdote can be memorable without proving a general claim. Explain why an insight matters through its substance rather than adding a generic “this is important” sentence.

Remove repetition across quick answers and insights. A quick answer says what the reader needs to know; an insight must add a mechanism, an illustrative calculation, concrete steps, an exception, or disagreement. It should not repeat the answer with more words.

For example, if an answer says “Count verification and revision time, not just generation time,” the insight should show a source-supported calculation or a comparison method. A second paragraph saying “The whole process matters” adds no information. If the episode supplies no deeper detail, omit that insight.

## 4. Preserve meaning while compressing

- Put the central question and takeaway at the top.
- Retain the strongest qualifying condition, meaningful disagreement, or exception next to the claim it changes. A footer disclaimer cannot repair an overstated answer.
- Attribute opinions, predictions, and recommendations to the speaker. Label a cross-passage inference as a synthesis.
- Keep names, figures, dates, and units exact when confirmed; otherwise omit or qualify them.
- Introduce participants only when source metadata or introductions establish their identity. Do not guess credentials or biographies.
- Include up to three short exact quotes only when their wording adds value.
- Include optional `open_questions` only for questions genuinely raised but left unresolved in the episode. They are not the Agent's speculative list of future research topics.
- Do not force action advice onto stories, fiction, comedy, history, or cultural discussions.
- Write in the user's language. Preserve original technical terms when translation would obscure meaning.

A 3–5 minute reading target is an editorial target, not a guarantee based on runtime or word count. Do not fill available space just because the validator allows it.

Review optional sections by purpose: a participant card helps interpret who is speaking; a quotation preserves wording that matters; an action enables a useful next step; an open question preserves an actual unresolved issue. If a section only duplicates an answer or insight, omit it.

## 5. Evidence and completion

Write `evidence.json` using the [output contract](output-schema.md). Reference source segments for the takeaway, each quick answer, and each insight. Cite all distant passages used in a synthesis. Time ranges must come from the actual transcript; untimed sources use segment IDs without fabricated times.

Run `finalize_bundle.py`, then `validate_bundle.py`. In `summary` mode, finalization generates `summary.md`, a compatibility `analysis.md`, and `reader.html` from the same validated evidence. Deliver the first and last of these with clickable links.

Check the result as a reader:

- Can I identify the episode's central question within a few seconds?
- After 30 seconds with the takeaway and direct answer sentences, do I have a useful understanding even if I stop reading?
- Do the questions express real stakes and give direct answers?
- Does each insight add something specific beyond what the answers already told me?
- Is the most consequential information first, and can low-value content be removed?
- Are reasoning, boundaries, and disagreements preserved where they change meaning?
- Does the result cover the episode rather than just an opening segment or search result?
- Can each main point be checked against its source?
- Can I finish the summary in a few minutes without reading processing details?

`ready_for_analysis` means the source is ready. Only successful finalization and validation justify calling the summary complete.

## Legacy compatibility

`quick`, `standard`, and `deep` are retained for callers that explicitly request the old contracts. They are not recommended alternatives for a normal podcast-summary request. Existing report integrations can keep their original `analysis.md`, claim ledger, and evidence structures; the default product follows the workflow above.
