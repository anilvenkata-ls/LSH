# Job 7 — Integration Testing

`IntegrationTestingAgent` · `src/rcm_change_platform/agents/a07_integration_tests.py` · step 7

## Purpose

Prove the change does not move any money. The job snapshots the financial
metrics from an unchanged warehouse, builds a second warehouse with the change
applied and the ETL replayed, and compares the two. Charges, payments,
adjustments, denials, AR balances, row counts and business key counts must be
identical.

This is the control the RCM team asked for after a prior AR balance incident. A
change that moves a dollar figure fails the run, full stop.

## Contract

**Reads**

| From | Used for |
| --- | --- |
| `context.impact` | The target fact table and the views to check for parity. |
| `context.change_set` | Required to exist; applied to the candidate sandbox. |
| `context.repo` | Columns on the fact table, business keys, view definitions. |
| `context.options.execute_tests` | Whether to run at all. |
| `context.scratch` | The candidate sandbox job 6 already built. |

**Writes**

| To | Contents |
| --- | --- |
| `context.integration_suite` | A `TestSuite`: one snapshot case per metric, plus reporting parity cases. |
| `context.integration_run` | A `TestRun` combining reconciliation results and parity results. |
| `context.reconciliation` | A `ReconciliationReport`: one line per metric with before, after, delta and verdict. |
| `context.scratch` | The baseline sandbox. |
| `context.warnings` | Which metrics drifted. |

## The metrics are derived, not hard-coded

`runner.financial_metrics(context)` builds the metric set from the catalog each
run:

1. The fact table's row count.
2. `SUM(col)` for each of `charge_amount`, `payment_amount`,
   `adjustment_amount`, `denial_amount`, `balance` **that the fact table
   actually has** — the `FINANCIAL_COLUMNS` tuple in `sandbox/runner.py` is a
   candidate list, filtered against the real columns.
3. `COUNT(DISTINCT key)` for each declared business key.
4. The row count of every impacted view, plus `SUM(balance)` or
   `SUM(total_balance)` where the view outputs one.

Against the bundled catalog that is 11 metrics: the fact table's row count, five
sums, one distinct business key count, and four more across the two impacted
views. With the 3 reporting parity cases, the run reports 14 integration checks.
A different warehouse produces a different, equally valid set without a code
change — which is the point. Adding a monetary column to the fact table
automatically brings it under reconciliation.

Note that step 4 iterates every view in the impact matrix, including those
marked `Review`. The aggregate summary view is not edited, but its totals are
still reconciled, because an unedited view reading a changed fact table can
still shift.

`view_output_columns` works out what a view exposes by parsing its projection
with `sqlkit`, taking the `AS` alias where there is one and the trailing
identifier otherwise.

## How it works

1. **Derive the metrics** and build the suite. Snapshot cases carry an empty
   assertion — they are documentation of the query that was run before and
   after, executed by the reconciliation path rather than the case runner.
2. **Snapshot the baseline.** `runner.baseline(context)` builds a sandbox from
   the catalog with no change applied and replays the ETL, then `snapshot`
   evaluates every metric.
3. **Snapshot the candidate.** `runner.candidate(context)` returns the sandbox
   job 6 already built — change applied, ETL replayed. `reconcile` evaluates the
   same metrics and pairs them with the baseline values into
   `ReconciliationLine`s.
4. **Run the parity cases**, which are the ones with a real assertion.
5. **Combine** reconciliation results and parity results into one `TestRun`.

The ordering constraint is absolute: the baseline snapshot must be taken from a
warehouse where the change has not been applied. The two sandboxes are separate
SQLite databases for exactly this reason, both cached in `context.scratch`.

### Reconciliation

`ReconciliationLine` compares before against after with a default tolerance of
`0.01`, which absorbs floating-point noise in summed decimals without hiding a
real difference. `matched` is `abs(after - before) <= tolerance`;
`ReconciliationReport.balanced` is true only when every line matches.

Every reconciliation result is `blocking`. There is no configuration to make
financial drift non-blocking, and adding one would defeat the job.

### Reporting parity

For each impacted view, up to three checks comparing the view against the fact
table:

| Check | Generated when | Asserts |
| --- | --- | --- |
| `parity::<view>::balance` | the view outputs `balance` | `SUM(balance)` equals the fact table's, within `0.01`. |
| `parity::<view>::total_balance` | the view outputs `total_balance` | Same, against the fact table's `SUM(balance)`. |
| `parity::<view>::row_count` | the view has no `GROUP BY` or `DISTINCT` | Row count equals the fact table's. |

The row count check is skipped for aggregating or deduplicating views, where a
different row count is correct behaviour rather than a defect.

## Halt conditions

| Condition | Message | What the user should do |
| --- | --- | --- |
| Missing impact or change set | *Integration testing requires the impact matrix and change set.* | Out-of-order pipeline; tests only. |
| Sandbox failure | *Integration run failed in the sandbox: …* | Read the database error; usually the ETL replay failing on an edited definition. |

Drift itself does **not** halt. The reconciliation lines are recorded as failed
results, a warning names the drifted metrics, and job 9 turns that into a
blocking checklist item so the CLI exits `1`. The reviewer gets the full
before/after table rather than an abrupt stop — which is more useful, because
the numbers are the diagnosis.

## Warnings

| Warning | Raised when |
| --- | --- |
| `Financial reconciliation drift detected for: <metrics>` | Any line is outside tolerance. |

## Key functions

| Function | Responsibility |
| --- | --- |
| `execute` | Sequences snapshot → apply → reconcile → parity. |
| `_build_suite` | Snapshot cases and the three parity case types. |
| `_reconciliation_results` | Turns reconciliation lines into `TestResult`s with a readable before/after/delta. |
| `runner.financial_metrics` | Derives the metric set from the catalog. |
| `runner.baseline` / `runner.candidate` | The two cached sandboxes. |
| `runner.view_output_columns` | What a view exposes, via `sqlkit`. |
| `WarehouseSandbox.snapshot` / `reconcile` | Evaluate the metrics; pair before with after. |

## Tests and extension points

Covered by `tests/test_agents_testing.py` and `tests/test_sandbox.py`. The
important one is the negative case: a change that silently drops rows must be
caught by reconciliation. If you change this job, keep that test passing — it is
the job's reason to exist.

When changing this job:

- **Never weaken the blocking severity of a reconciliation line.** If a metric
  is too noisy, the fix is a better metric or a justified tolerance on that
  line, not a downgrade.
- **New financial columns need no code change** if they are named in
  `FINANCIAL_COLUMNS`; adding a name there brings every warehouse that has the
  column under reconciliation.
- **Both sandboxes must stay independent.** Sharing one connection between
  baseline and candidate would silently destroy the comparison, and nothing else
  in the pipeline would notice.
- **The tolerance is per line.** `ReconciliationLine.tolerance` defaults to
  `0.01` and `reconcile` applies one value to all lines. If a specific metric
  needs a different tolerance, set it on the line rather than widening the
  default for everything.
