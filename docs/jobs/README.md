# The ten RCM jobs

This directory documents the ten jobs that make up the change automation
pipeline. One page per job. Start here, then open the page for the job you are
working on.

If you have not read [`AGENTS.md`](../../AGENTS.md) yet, read it first — it
covers the repository layout and the rules a change must not break.

## How to read these pages

Every job page has the same seven sections, so you can jump straight to the one
you need:

1. **Purpose** — what the job is responsible for, in two sentences.
2. **Contract** — what it reads from `ChangeContext` and what it writes back.
   This is the part that matters most: jobs never call each other, they only
   read and write the shared context.
3. **How it works** — the algorithm, including the judgement calls.
4. **Halt conditions** — every way the job can stop the pipeline, the message
   the user sees and what they should do about it.
5. **Warnings** — non-fatal observations the job appends to `context.warnings`.
6. **Key functions** — the methods worth knowing, by name.
7. **Tests and extension points** — where the job is covered and what to be
   careful about when changing it.

These pages describe the jobs and the parts of the supporting modules the jobs
depend on. The supporting modules are documented in their own docstrings;
`sqlkit.py`, `catalog/lineage.py` and `sandbox/warehouse.py` in particular are
worth reading directly if you are changing jobs 3, 4, 6 or 7.

## The pipeline

Jobs run in the order given by `PIPELINE` in
`src/rcm_change_platform/agents/__init__.py`. Order is load-bearing: each job
depends on fields written by the ones before it.

| # | Job | Page | Produces |
| --- | --- | --- | --- |
| 1 | Request Intake | [01](01-request-intake.md) | `context.request` |
| 2 | Metadata Discovery | [02](02-metadata-discovery.md) | `context.metadata` |
| 3 | Impact Analysis | [03](03-impact-analysis.md) | `context.impact` |
| 4 | SQL Change Generation | [04](04-sql-change-generation.md) | `context.change_set` |
| 5 | Documentation | [05](05-documentation.md) | `context.documents` |
| 6 | Unit Test Generation | [06](06-unit-test-generation.md) | `context.unit_suite`, `context.unit_run` |
| 7 | Integration Testing | [07](07-integration-testing.md) | `context.integration_suite`, `context.integration_run`, `context.reconciliation` |
| 8 | Power BI Impact | [08](08-power-bi-impact.md) | `context.power_bi` |
| 9 | Deployment Readiness | [09](09-deployment-readiness.md) | `context.checklist` |
| 10 | Final Output | [10](10-final-output.md) | `context.package`, the files on disk |

The shared machinery — `ChangeContext`, the `Agent` base class, halting and
salvage — is documented in [pipeline-contracts.md](pipeline-contracts.md).

## What a run looks like

A successful run against the bundled catalog. The summaries are abbreviated
here; the real run report prints the full line each job returns:

```
 1. request_intake         completed  parsed 'Patient Financial Class' for report 'AR Aging Report'
 2. metadata_discovery     completed  resolved to rcm.dim_patient.patient_financial_class VARCHAR(50)
 3. impact_analysis        completed  11 impacted objects, 4 require code changes
 4. sql_change_generation  completed  generated migration for rcm.fact_ar.patient_financial_class
 5. documentation          completed  drafted 5 documents
 6. unit_test_generation   completed  8/8 unit tests passed
 7. integration_testing    completed  14/14 integration checks passed; reconciliation balanced
 8. power_bi_impact        completed  14 Power BI actions for dataset 'pb_ar_aging'
 9. deployment_readiness   completed  15/16 checklist items complete; ready for deployment
10. final_output           completed  wrote 15 artifacts to out/Change_Request
```

The value travels this route, which job 3 records as the propagation path:

```
rcm.dim_patient → rcm.sp_load_ar_fact → rcm.fact_ar → rcm.vw_ar_detail → pb_ar_aging → AR Aging Report
```

## Which job owns which artifact

Job 10 writes every file, but the content usually belongs to an earlier job.
When an artifact looks wrong, fix the job in the *owns* column, not the writer.

| File | Content owned by | Written by |
| --- | --- | --- |
| `Requirement.md` | 5 (via `rendering.requirement`) | 10 |
| `Technical_Design.md` | 5 (via `rendering.technical_design`) | 10 |
| `PR_Description.md` | 5 (via `rendering.pr_description`) | 10 |
| `Release_Notes.md` | 5 (via `rendering.release_notes`) | 10 |
| `Validation_Report.md` | 5 (via `rendering.validation_report`) | 10 |
| `Validation_Report.pdf` | 5 (rendered from the markdown) | 10 |
| `Generated_SQL.sql` | 4 (assembled by `deployment_script`) | 10 |
| `Rollback_Script.sql` | 4 (`change_set.rollback_sql`) | 10 |
| `Unit_Tests.sql` | 6 (the suite, annotated with its results) | 10 |
| `Integration_Tests.sql` | 7 (the suite, annotated with its results) | 10 |
| `Impact_Analysis.xlsx` | 3, 7, 8 (one sheet each, plus tests) | 10 |
| `Impact_Analysis.csv` | 3 (the impact matrix) | 10 |
| `PowerBI_Change_Plan.md` | 8 (`context.power_bi`) | 10 |
| `Deployment_Checklist.md` | 9 (`context.checklist`) | 10 |
| `Run_Manifest.json` | all jobs | 10, then rewritten by the orchestrator |

The manifest is written twice on purpose: job 10 writes it, then
`ChangePipeline.run` writes it again so that job 10's own `AgentReport` is
included.

## Documents are rendered twice

Job 5 renders the documents mid-pipeline, before the tests have run. Job 10
calls `refresh_documents` and renders them again, now that test results,
reconciliation and the readiness verdict exist. The renderers in `rendering.py`
are pure functions of the context, which is what makes rendering twice safe.

The consequence to remember: **a document written by job 5 and never refreshed
is what a halted run produces.** That is the intended behaviour — the requester
gets the evidence gathered so far plus the clarification question.

## When a job halts

Any job can call `context.halt(name, reason)`. The pipeline stops there, then
runs the salvage jobs (5 and 10) if they have not run yet, so a package is still
produced. The CLI exits `2`.

Every halt condition in the pipeline, in one place:

| Job | Condition |
| --- | --- |
| 1 | The request is empty |
| 1 | Could not identify both a column and a report |
| 1 | The report is not in the catalog |
| 1 | The change type is not `add_column` |
| 2 | The phrase does not resolve to a certified column |
| 3 | No fact table feeds the report |
| 3 | No stored procedure loads that fact table |
| 3 | The source table is not joinable to the procedure's inputs |
| 4 | The procedure or view named in the matrix is missing from the catalog |
| 6 | The generated SQL fails to execute in the sandbox |
| 7 | The integration run fails in the sandbox |
| 8 | The report has no Power BI metadata |

Jobs 5, 9 and 10 have no halt conditions — by design, since they are the jobs
that have to work even when something else has gone wrong.

Two mechanisms produce a halt, and they are reported differently:

- An explicit `context.halt(...)` gives the job the status `halted`.
- An uncaught exception is turned into a halt by `Agent.run`, with the status
  `failed` and the exception text as the summary. Job 4 is the only job that
  relies on this, for a catalog object that the impact matrix named but the
  repository does not have.

Jobs 2, 3, 4, 6, 7 and 8 also open with a guard that halts when an upstream
field is missing. Those fire only if the pipeline is assembled out of order, so
you will meet them when writing tests rather than in a real run.

## Running one job

Use the `run_agents` fixture from `tests/conftest.py`. It runs a prefix of the
pipeline and hands back the context, which is the only sane way to set up the
preconditions a later job needs:

```python
from rcm_change_platform.agents import (
    RequestIntakeAgent, MetadataDiscoveryAgent, ImpactAnalysisAgent,
)

def test_join_plan(run_agents):
    context = run_agents((RequestIntakeAgent, MetadataDiscoveryAgent, ImpactAnalysisAgent))
    assert context.impact.join_plan["strategy"] == "existing_join"
```

To change what the catalog says, use the `make_repo` fixture, which deep-copies
the seeds and applies a mutation. Several halt conditions are tested this way —
by removing a relationship or a procedure from the catalog and asserting the
pipeline stops.
