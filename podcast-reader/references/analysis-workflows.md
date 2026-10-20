# Summary workflow

The default task is a concise, evidence-backed podcast summary organized around **the important questions, why they matter, and how far the episode answers them**. Identify the questions before drafting answers or selecting insights.

The main sequence is: **read the complete material → establish the core question → collect candidate questions → rank and merge → verify answer coverage → add supporting insights**. In the first 30 seconds, readers should see what is at stake and where the episode has or lacks an answer. A closer read adds evidence, mechanisms, examples and exceptions.

For a substantial episode, target approximately **900–1,600 Chinese characters or 500–900 English words** across the visible summary. These are editorial ranges, not minimums, schema limits, or a reason to pad a short episode. The renderer estimates reading time from the finished text; the target does not justify displaying a fixed reading time.

## 1. Establish coverage

Read source metadata, the transcript quality report, and the full chunk inventory. Inspect the transcript in bounded batches across every substantive part of the episode. Track its central question, major turns, conclusions, disagreements, and exceptions.

A keyword search is useful for verification after broad reading; a few top-ranked hits are not sufficient evidence for a whole-episode summary. Check neighboring chunks when a speaker qualifies a point or responds to someone else. Do not erase a later correction because an earlier statement is easier to summarize.

If the source is partial, summarize only the available content and explicitly state the scope. Metadata-only preparation cannot produce an episode summary.

## 2. Build the question map

### Establish the core question

Write `digest.core_question` as the specific problem that holds the episode together. A topic such as “AI tools” is not a question. A broad prompt such as “What can we learn?” says nothing about this episode.

In the fictional example, the core question is: “普通人怎样判断 AI 真正帮上了工作，而不是只学会了一个工具？” It identifies the subject and the tension between tool familiarity and useful outcomes.

### Collect candidates and distinguish their origins

Read the complete transcript before deciding which questions deserve a place. Collect:

- `explicit`: the source clearly asks this question; faithful rephrasing is allowed.
- `synthesized`: the Agent derives a useful question from a substantive discussion, example, contradiction or unresolved point.

Both kinds must be grounded in source passages. Do not present a synthesized question as something the host literally asked. Do not invent an unrelated question simply because it is interesting.

### Rank, merge and make each question stand alone

Rank candidate questions by impact on understanding or decisions, information value, and meaningful issues the source actually leaves unresolved. Merge duplicates only when their scopes and answer coverage match. An episode's most consequential unanswered question may outrank a minor answered one.

Each selected question should retain its subject, conflict and essential conditions when read outside the page. Do not enforce a 6–16 character target that strips away the problem:

| Reject | Specific question |
|---|---|
| 从哪开始？ | 普通人初学 AI，怎样选一个适合开始的小任务？ |
| 怎么算有效？ | AI 出稿更快，怎样判断整个任务是否真的省时？ |
| 有哪些启示？ | 手动配合 AI 的流程满足什么条件，才值得自动化？ |

Usually select 3–6 questions; use fewer when the source supports fewer. Do not pad the list or force one of every category.

### Check the actual answer coverage

For every `quick_takes` item, newly generated summaries require:

1. `question`: a concrete, independently understandable question.
2. `why_it_matters`: the source-supported stakes or judgment that depends on it. Do not invent audience motives or hypothetical harms.
3. `question_origin`: `explicit` or `synthesized`.
4. `answer_status`: `answered`, `partial`, or `unanswered`.
5. `answer`: what the episode actually says, including relevant conditions.
6. `evidence`: references supporting the question's origin, stakes and answer scope.
7. `gap`: required for `partial` or `unanswered`; omitted for `answered`.

Re-read both the initial response and later follow-ups. `answered` means the episode addresses the selected question's scope. `partial` means a material part remains unresolved. `unanswered` means it supplies no answer. **These statuses are not truth ratings, confidence levels, or external fact checks.**

An episode may explain why no universal threshold exists while leaving a practical criterion unresolved. In the fictional example, “一个 AI 流程要验证多少次，才能认定稳定？” is `partial`: the speaker explains that task differences and error costs prevent a universal count, but offers no scenario-specific verification count or stability test. Do not force it to `unanswered` merely to demonstrate that badge.

State the precise missing piece in `gap`; do not add a speculative research agenda. Keep important incomplete answers among the question cards and do not repeat them in `open_questions`.

Lead the answer with the source's actual response. Chinese answers may often fit in 30–60 characters, but the question's full scope and decisive caveats take priority. References must cover the question and its response, including distant passages used to establish why it matters or what remains open.

## 3. Add information that deepens the selected questions

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
- Show important missing or incomplete answers directly in their question cards using `answer_status` and `gap`. `open_questions` remains a legacy field; do not duplicate the cards there.
- Do not force action advice onto stories, fiction, comedy, history, or cultural discussions.
- Write in the user's language. Preserve original technical terms when translation would obscure meaning.

A 3–5 minute reading target is an editorial target, not a guarantee based on runtime or word count. Do not fill available space just because the validator allows it.

Review optional sections by purpose: a participant card helps interpret who is speaking; a quotation preserves wording that matters; an action enables a useful next step; an open question preserves an actual unresolved issue. If a section only duplicates an answer or insight, omit it.

## 5. Evidence and completion

Write `evidence.json` using the [output contract](output-schema.md). All new summaries require `core_question` and the complete question-card fields above; older bundles may remain compatible without them. Reference source segments for the core question/takeaway, each question's stakes and response, and each insight. Cite all distant passages used in a synthesis. Time ranges must come from the actual transcript; untimed sources use segment IDs without fabricated times.

Run `finalize_bundle.py`, then `validate_bundle.py`. In `summary` mode, finalization generates `summary.md`, a compatibility `analysis.md`, and `reader.html` from the same validated evidence. Deliver the first and last of these with clickable links.

Check the result as a reader:

- Can I identify the episode's central question within a few seconds?
- After 30 seconds, can I explain the important questions, their stakes, and which ones the episode actually answers?
- Can I understand every question without its title or neighboring cards?
- Are explicit source questions and Agent-derived questions distinguished?
- Does each answer address its question's actual scope, with a precise gap where it does not?
- Does each insight add something specific beyond what the answers already told me?
- Is the most consequential information first, and can low-value content be removed?
- Are reasoning, boundaries, and disagreements preserved where they change meaning?
- Does the result cover the episode rather than just an opening segment or search result?
- Can each main point be checked against its source?
- Can I finish the summary in a few minutes without reading processing details?

`ready_for_analysis` means the source is ready. Only successful finalization and validation justify calling the summary complete.

## Legacy compatibility

`quick`, `standard`, and `deep` are retained for callers that explicitly request the old contracts. They are not recommended alternatives for a normal podcast-summary request. Existing report integrations can keep their original `analysis.md`, claim ledger, and evidence structures; the default product follows the workflow above.
