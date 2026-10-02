# Job 1 — Request Intake

`RequestIntakeAgent` · `src/rcm_change_platform/agents/a01_intake.py` · step 1

## Purpose

Turn the sentence a business user typed into a structured `ChangeRequest`, and
confirm the report they named actually exists in the catalog. This is the job
that decides whether the pipeline can proceed at all, so it is deliberately
quick to refuse: an unparsable request halts here with a question rather than
producing a confident guess downstream.

## Contract

**Reads**

| From | Used for |
| --- | --- |
| `context.raw_request` | The sentence to parse. |
| `context.repo.reports` | Resolving the report phrase, and listing near misses when it fails. |
| `context.llm` | Optional structured extraction. |
| `context.options` | `business_reason`, `requested_by` and `request_id` override what was parsed. |

**Writes**

| To | Contents |
| --- | --- |
| `context.request` | A `ChangeRequest`: report, requested column, business reason, change type, requester, confidence, parser, request id, clarifications. |

`context.request` is set even on the halt paths, which is what lets the salvage
run render a `Requirement.md` containing the clarification question.

## How it works

1. **Reject an empty request** immediately.
2. **Parse**, LLM first and rules second. `_parse_with_llm` asks for JSON with
   `report`, `requested_column`, `business_reason` and `change_type`, passing
   the known report names as context. It returns `None` — and the rule parser
   takes over — when no provider is configured, the call fails, the reply is not
   JSON, or either of column and report came back empty.
3. **Rule parsing** (`_parse_with_rules`) runs in a fixed order:
   - Strip a trailing reason clause (`because …`, `so that …`, `needed for …`,
     `reason: …`) and remember it. This happens first so the reason text cannot
     be mistaken for part of the report name.
   - Match the remaining sentence against two shapes: the verb form (*add /
     include / append / surface / expose / show* `<column>` *to / on / in*
     `<report>`) and the need form (`<report>` *needs / requires* `<column>`).
   - Clean both captures: strip quotes and articles, drop a trailing
     `column` / `field` / `attribute`, and repeatedly strip trailing nouns like
     `report` or `dashboard` from the report phrase.
   - A quoted phrase anywhere in the original request wins over the regex
     capture for the column, because a user who quotes a phrase means it
     literally.
4. **Score the parse**: `0.9` from the LLM, `0.75` when the rules matched and
   the request contained a quoted phrase, `0.6` for a plain regex match, `0.5`
   when only a quoted phrase was found.
5. **Resolve the report** against the catalog with `repo.find_report`, which
   fuzzy-matches the phrase against each report's name and aliases with a
   threshold of `0.4`. On success the request's `report` is replaced by the
   canonical catalog name, so every later job works with one spelling, and the
   confidence is raised to the **larger of the parse score and the report match
   score**. An exact report name therefore reports confidence `1.00` even
   though the rule parser only scored its own work `0.75`.
6. **Assign a request id** — `--request-id` if given, otherwise `CR-` plus the
   first eight hex characters of the SHA-1 of the raw request, uppercased. The
   same sentence therefore always produces the same id, which keeps artifacts
   diffable between runs.

## Halt conditions

| Condition | Message | What the user should do |
| --- | --- | --- |
| Empty request | *Empty request: nothing to analyse.* | Supply a request. |
| Column or report missing after parsing | *Could not identify both the requested column and the target report.* | Rephrase as `Add "<column>" to the <report> report`. |
| Report not in the catalog | *No report in the catalog matches '…'. Closest entries: …* | Use one of the suggested names, or add the report to `power_bi.json`. |
| Change type is not `add_column` | *Only column additions are automated today; the request was logged for manual triage.* | Handle manually; see the extension note below. |

The report halt lists the three closest catalog entries with their scores, so
the clarification is actionable rather than a bare rejection.

## Warnings

None. This job either succeeds or halts.

## Key functions

| Function | Responsibility |
| --- | --- |
| `execute` | Orchestrates parse → validate → resolve, and owns all four halt paths. |
| `_parse_with_llm` | Structured extraction; returns `None` on any problem so the caller falls back. |
| `_parse_with_rules` | The deterministic grammar: reason, then shape, then quoted-phrase override. |
| `_clean_column` / `_clean_report` | Strip quotes, articles and trailing nouns from the captures. |
| `_request_id` | Stable `CR-` id derived from the request text. |
| `repo.find_report` | Fuzzy match over report names and aliases (in `catalog/repository.py`). |
| `text.similarity` | The scorer: the better of sequence ratio and a blend of Jaccard and containment over stopword-filtered tokens. |

## Tests and extension points

Covered by `tests/test_agents_intake_metadata.py` (parsing shapes, report
resolution, the halt paths) and `tests/test_llm.py` (the LLM path and its
fallback).

When changing this job:

- **New phrasings go in `_REQUEST_PATTERNS`**, not into the LLM prompt. The rule
  path is what the tests exercise and what runs in CI, where no key is set.
- **`_TRAILING_NOISE` is applied in a loop** so `AR Aging Report dashboard`
  reduces correctly. Keep it idempotent if you add words to it.
- **Supporting a new change type** means more than widening the `ChangeType`
  enum. Jobs 4, 6 and 7 all assume a column is being added; a rename or a
  datatype change needs its own generation and test strategy. Until that exists,
  halting here is the correct behaviour, not a limitation to work around.
- **The confidence score is advisory.** Nothing downstream gates on it; it is
  printed and recorded so a reviewer can see how sure the parse was. If you want
  it to gate, that is a product decision to make explicitly.
