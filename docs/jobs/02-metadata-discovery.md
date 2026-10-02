# Job 2 — Metadata Discovery

`MetadataDiscoveryAgent` · `src/rcm_change_platform/agents/a02_metadata_discovery.py` · step 2

## Purpose

Resolve the business phrase from job 1 — "Patient Financial Class" — to a
physical column — `rcm.dim_patient.patient_financial_class VARCHAR(50)` — and
attach the evidence trail that justifies the choice. Everything downstream
depends on this being right, so the job records *where* each fact came from
rather than just the answer.

## Contract

**Reads**

| From | Used for |
| --- | --- |
| `context.request` | The phrase to resolve and the report name. |
| `context.repo` | Data dictionary terms, information schema columns, Jira tickets, documentation. |
| `context.graph` | Upstream producers of the resolved column's table. |
| `context.llm` | Breaking ties between near-identical candidates. |

**Writes**

| To | Contents |
| --- | --- |
| `context.metadata` | A `MetadataDocument`: the resolved `ColumnMetadata`, candidates, upstream dependencies, related tickets and documents, and the evidence list. |
| `context.warnings` | Uncertified column; PII column. |

`context.metadata` is set on the unresolved path too, carrying the candidates
and `unresolved_reason`, so the salvage documents can show what was considered.

## How it works

Resolution is a cascade. The first source that produces an answer wins, and
every source consulted is appended to `document.evidence` whether or not it
matched.

1. **Data dictionary first.** `repo.find_term` fuzzy-matches the phrase against
   each term's `business_term` and its `synonyms`, with a threshold of `0.5`.
   This is what makes "fin class" resolve. A match is recorded as evidence
   regardless of outcome.
2. **Confirm against the information schema.** A dictionary term names a
   physical table and column; `_from_term` looks it up to pick up the real data
   type and nullability. If the physical column is missing, the dictionary is
   stale: the job warns and falls through to step 3 rather than trusting the
   dictionary alone.
3. **Fall back to a physical column search.** `repo.find_physical_columns`
   scores every column in every table, taking the better of the similarity to
   the column name and 0.8 × the similarity to its description — the
   discount encodes that a name match is stronger evidence than a prose match.
   The top five become the candidate list.
4. **Disambiguate.** `_disambiguate` takes the top candidate, then collects
   every candidate within `0.05` of it. If more than one is that close *and* an
   LLM is available, it asks which one fits the phrase, and marks the winner's
   `matched_on` as `llm:<provider>`. Otherwise the top candidate stands.
5. **Apply the acceptance threshold.** A fallback candidate is only accepted at
   `match_score >= 0.62` (`_DIRECT_MATCH_THRESHOLD`). Below that the job halts.
   Note the asymmetry: a dictionary term that cleared `0.5` is accepted, because
   a curated synonym is better evidence than a string resemblance.
6. **Gather context** for the resolved column, each step adding evidence:
   upstream producers from the lineage graph, Jira tickets mentioning the table
   or the report, and documentation mentioning either.
7. **Raise governance warnings** for a column that is not `certified`, or is
   flagged `pii`. These do not stop the run here — they become checklist items
   in job 9, and the PII one blocks the release there.

## Halt conditions

| Condition | Message | What the user should do |
| --- | --- | --- |
| No structured request | *No structured request available.* | Pipeline assembled out of order; only reachable in tests. |
| Phrase does not resolve | *'…' could not be resolved to a certified column. Closest candidates: …* | Add a dictionary term or a synonym, or name the physical column directly. |

The unresolved message lists the three closest candidates as
`table.column (score)`, so a human can usually answer it in one line.

## Warnings

| Warning | Raised when | Consequence |
| --- | --- | --- |
| Column not certified, confirm with the data steward | `certified` is false on the dictionary term | Non-blocking checklist item in job 9, naming the steward. |
| Column flagged as PII, confirm the audience | `pii` is true | **Blocking** checklist item in job 9. |
| Dictionary term points at a missing column | The term names a table/column absent from the information schema | The job continues via the physical search. |

## Key functions

| Function | Responsibility |
| --- | --- |
| `execute` | Runs the cascade, then gathers context and raises governance warnings. |
| `_resolve_column` | The cascade itself; returns the chosen column and all candidates. |
| `_from_term` | Builds `ColumnMetadata` from a dictionary term plus the physical column. |
| `_disambiguate` | Near-tie detection and the optional LLM tie-break. |
| `_upstream` / `_tickets` / `_documents` | Context gathering, each appending evidence. |
| `repo.find_term`, `repo.find_physical_columns` | The two search surfaces, in `catalog/repository.py`. |

## The evidence list

`MetadataEvidence` has three fields — `source`, `reference`, `detail` — and a
successful run produces five entries, in this order: Data Dictionary,
Information Schema, Column Lineage Repository, Jira, Existing Documentation.
They are rendered into `Requirement.md` as the audit trail for the resolution.

Entries are appended even when a source finds nothing, recorded as `no match` or
`none recorded`. That is deliberate: "we checked Jira and there was no history"
is useful information for a reviewer, and its absence would be ambiguous.

## Tests and extension points

Covered by `tests/test_agents_intake_metadata.py`, including the stale-dictionary
fallback and the unresolved halt. `tests/test_llm.py` covers the tie-break.

When changing this job:

- **The two thresholds mean different things.** `0.5` in `find_term` gates a
  curated synonym match; `0.62` in `_DIRECT_MATCH_THRESHOLD` gates an uncurated
  string match. Raising the second makes the pipeline refuse more often, which
  is the safe direction; lowering it risks resolving to a plausible wrong
  column, and the rest of the pipeline will not catch that.
- **Adding an evidence source** means appending to `evidence` in the same
  shape. `rendering.requirement` iterates the list, so new sources appear in
  the requirement document without a renderer change.
- **The job resolves a column, not a column plus a path.** Where the value can
  physically travel is job 3's problem. Keep that split — it is why an
  unresolvable column and an unreachable column produce different messages.
