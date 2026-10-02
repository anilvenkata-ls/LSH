# Job 9 — Deployment Readiness

`DeploymentReadinessAgent` · `src/rcm_change_platform/agents/a09_deployment_readiness.py` · step 9

## Purpose

Turn everything the previous jobs produced into a checklist and a single
blocking verdict. The rule that makes the checklist worth reading: **every item
is derived from evidence that exists, not asserted.** A test that was generated
but never executed leaves its item outstanding. A checklist of green ticks that
nobody can trace back to a result is decoration; this one is auditable.

The verdict becomes the CLI exit code, which is what lets the platform gate a CI
pipeline.

## Contract

**Reads**

Nearly the whole context: `change_set`, `impact`, `unit_suite`, `unit_run`,
`integration_run`, `reconciliation`, `power_bi`, `documents`, `metadata`, and
`repo` for the already-present column check.

**Writes**

| To | Contents |
| --- | --- |
| `context.checklist` | A `DeploymentChecklist`: the items in section order, plus the blockers list. |

`DeploymentChecklist.ready` is `not blockers`. Blockers are the items that are
`blocking` and not `complete`, formatted as `<section>: <item> - <detail>`.

## The sections

Five sections, built in order. Against the bundled catalog the run produces 16
items, 15 complete.

### Development

| Item | Complete when | Blocking |
| --- | --- | --- |
| Migration script generated | A migration exists, **or** the column was already on the fact table | yes |
| Stored procedure updated | The set of procedures generated equals the set the matrix marked `Modify` | only if any were expected |
| View updated | Same, for views | only if any were expected |
| Rollback script generated | `rollback_sql` is non-empty | yes |

The first item's "or already present" branch is why a re-run against a warehouse
that already has the column does not report a false failure. The procedure and
view items compare **sets**, so a procedure the matrix expected but job 4 did
not produce is caught — the two jobs are checked against each other rather than
trusted.

`blocking=False` when nothing of that type was expected, with the detail *no
change required*, so a change touching no views does not block on a view edit
that was never needed.

### Testing

| Item | Complete when | Blocking |
| --- | --- | --- |
| Unit tests generated | The suite has at least one case | yes |
| Unit tests passed | The run executed **and** `TestRun.passed` | yes |
| Integration tests passed | Same, for the integration run | yes |
| Financial reconciliation passed | The report executed **and** `balanced` | yes |

`executed and passed` is the whole point. With `--no-execute`, the suites are
generated, the runs are marked not executed, and these three items stay
outstanding — so a generation-only run is correctly reported as not ready.

`_test_detail` distinguishes the three states a reviewer cares about: *not
generated*, *generated but not executed*, and the names of the failing cases.

### Reporting

| Item | Complete when | Blocking |
| --- | --- | --- |
| Power BI change plan generated | The plan has at least one action | yes |
| Semantic model refresh scheduled | `refresh_required` is true | only when a refresh is required |
| Report visuals reviewed by a human | never — always outstanding | no |

The last item is permanently incomplete by design. It is a manual step with the
detail *place the new field on the intended visuals*, non-blocking so it does
not stop the release, but present so it cannot be forgotten. This is the single
incomplete item in a healthy run — the 16th of 16.

The refresh item is both complete and blocking when a refresh is required, and
neither when it is not, which is how a DirectQuery dataset avoids an item that
can never be satisfied.

### Documentation

One item each for `Technical_Design.md`, `PR_Description.md` and
`Release_Notes.md`, complete when the rendered content exceeds 200 characters.

That threshold is a liveness check, not a quality judgement: every renderer
returns a short explanatory string when its inputs are missing, and those fall
under 200 characters. So the item catches a document that degraded on a halt
path, which is exactly the case where the release should be blocked.

### Governance

| Item | Complete when | Blocking |
| --- | --- | --- |
| Column certified in the data dictionary | `certified` is true | no — detail names the steward |
| PII review | the column is **not** flagged PII | yes, when it is |

Certification is advisory because an uncertified column is a data governance
debt, not a safety problem. PII is blocking because showing a PII column to an
unapproved report audience is a compliance incident. Both originate as warnings
in job 2 and become decisions here.

## Halt conditions

None. This job must produce a verdict even when the run went badly — a halted
run still gets a checklist showing exactly which evidence is missing.

## Warnings

None of its own.

## Key functions

| Function | Responsibility |
| --- | --- |
| `execute` | Builds the five sections, computes the blockers, summarises. |
| `_development` / `_testing` / `_reporting` / `_documentation` / `_governance` | One section each. |
| `_test_detail` | The three-state description of a `TestRun`. |
| `DeploymentChecklist.ready` | `not blockers`. |
| `DeploymentChecklist.sections` | Section names in first-seen order, used by job 10's markdown. |
| `ChecklistItem.marker` | `[x]` or `[ ]` for the rendered checklist. |

## How the verdict reaches CI

```
context.halted              → exit 2   a job stopped; a human must answer something
checklist.ready is False    → exit 1   the change is understood but blocked
otherwise                   → exit 0   ready for deployment
```

Set in `cli._run`. The three-way split matters: exit `1` means the analysis
succeeded and found a problem, exit `2` means the analysis could not be
completed. A CI job should treat them differently.

## Tests and extension points

Covered by `tests/test_agents_reporting_release.py`, including the blocked
verdict when tests are not executed.

When changing this job:

- **Never mark an item complete from an expectation.** Derive it from a value
  another job wrote. The moment an item asserts rather than checks, the
  checklist stops being evidence.
- **Choose `blocking` deliberately.** It decides whether the CLI exits `1`, and
  therefore whether a pipeline stops. The existing non-blocking items —
  certification, visual review — are the ones a human can reasonably accept.
- **`blocking` can be conditional.** Several items compute it from the context
  so an item that cannot apply does not block. Prefer that to omitting the item,
  because an omitted item is invisible to the reviewer.
- **Adding a document to job 5 does not add a checklist item.** The
  documentation section names three files explicitly. That is intentional — not
  every generated document is release-critical — but it means a new critical
  document needs a line here.
