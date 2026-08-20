# Analysis workflows

Select only the modules needed for the user's intent. All episode-specific conclusions remain traceable to transcript or visual timestamps.

## Quality model

Every high-quality report answers four questions:

1. **What happened?** Accurate chaptered account.
2. **What is the reasoning?** Thesis, evidence, assumptions, objections, conclusions.
3. **How trustworthy is it?** Source quality, transcript confidence, missing evidence, contradictions.
4. **What can the user do with it?** Decisions, actions, study materials, or further research.

## Full decomposition

1. State the episode's central question and its most defensible answer.
2. Segment by semantic topic shifts, not equal time slices.
3. For each segment identify speaker, claim, evidence/example, assumption, counterpoint, and transition.
4. Connect segments into an argument map without erasing disagreements.
5. Separate episode statements from analyst synthesis and external verification.
6. End with implications, action conditions, risks, unresolved questions, and confidence limits.

## Argument map

Represent the reasoning as:

`central question → thesis → supporting premises → examples/data → assumptions → objections → responses → conclusion`

An anecdote may illustrate a premise but does not automatically prove it. Absence of an objection in the episode does not mean no objection exists.

## Claim ledger

| Field | Allowed values / meaning |
|---|---|
| Claim | Concise normalized proposition |
| Speaker | Name or unknown label |
| Kind | fact, opinion, anecdote, prediction, recommendation, synthesis |
| Evidence | One or more timestamp ranges |
| Support | stated, illustrated, argued, asserted, contradicted |
| Confidence | high, medium, low |
| Verification | not_checked, supported, mixed, contradicted, not_verifiable |

Do not fact-check every claim automatically. Prioritize current, consequential, surprising, quantitative, or high-stakes claims.

## Speaker and disagreement analysis

Track positions over time. Report a change of mind only when later language meaningfully revises an earlier position. Distinguish substantive disagreement, different definitions, different time horizons, and complementary perspectives. Do not infer personality or motive from tone unless the user explicitly requests rhetorical analysis and the evidence supports it.

## Topic research within an episode

1. Search exact topic, aliases, related entities, and translated terms.
2. Retrieve adjacent chunks around each hit.
3. Group findings by subtopic and chronology.
4. Include negative evidence and challenges, not only repeated supportive mentions.
5. State whether the topic is central, recurring, incidental, or absent.

## Cross-episode comparison

Build one bundle per episode, then align:

- publication date and historical context;
- definitions and scope;
- comparable claims and evidence;
- speaker incentives/roles;
- agreements, contradictions, and evolution;
- confidence and transcript quality.

Do not treat a later difference as contradiction when facts or context changed.

## Fact-check

For each selected claim:

1. Quote or paraphrase the episode claim with timestamp.
2. Normalize it into a verifiable proposition.
3. Define date, geography, population, and metric.
4. Research authoritative current sources.
5. Label `supported`, `mixed`, `contradicted`, `outdated`, or `not verifiable`.
6. Explain the gap without rewriting what the episode originally said.

## Learning and repurposing

Learning outputs may include definitions, concept relationships, recall questions, application exercises, and flashcards. Generated examples must be labeled as generated.

Repurposed articles, newsletters, show notes, and posts are transformations. Preserve attribution, avoid fabricated quotes, and do not make the rewritten voice appear to be the speaker's exact words.
