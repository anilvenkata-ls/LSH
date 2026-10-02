# RCM Change Automation Platform

An agent pipeline that takes a plain English request from a business user —

> Add Patient Financial Class to the AR Aging Report

— and produces the impact analysis, the SQL changes, executed tests, a Power BI change plan,
the documentation and a deployment-ready change package for a revenue cycle management (RCM)
data platform.

The generated SQL is not just text. The platform materialises the catalog into an in-memory
warehouse, applies the change, replays the ETL and reconciles charges, payments, adjustments,
denials and AR balances before and after. A change that moves a dollar figure fails the run.

```bash
pip install -e .
rcm-change run "Add Patient Financial Class to the AR Aging Report" --reason "Needed for payer analysis"
```

```
   1. request_intake           completed  parsed 'Patient Financial Class' for report 'AR Aging Report'
   2. metadata_discovery       completed  resolved to rcm.dim_patient.patient_financial_class VARCHAR(50)
   3. impact_analysis          completed  11 impacted objects, 4 require code changes
   4. sql_change_generation    completed  generated migration for rcm.fact_ar.patient_financial_class
   5. documentation            completed  drafted 5 documents
   6. unit_test_generation     completed  8/8 unit tests passed
   7. integration_testing      completed  14/14 integration checks passed; reconciliation balanced
   8. power_bi_impact          completed  14 Power BI actions for dataset 'pb_ar_aging'
   9. deployment_readiness     completed  15/16 checklist items complete; ready for deployment
  10. final_output             completed  wrote 15 artifacts to out/Change_Request
```

The command exits `0` when the change is deployment ready, `1` when the checklist is blocked and
`2` when an agent halted and needs a human answer, so it can gate a CI job.

## What you get

```
out/Change_Request/
├─ Requirement.md            structured requirement plus the metadata evidence trail
├─ Technical_Design.md       source, data flow, impact matrix, diffs, risks, rollback strategy
├─ Impact_Analysis.xlsx      impact matrix, lineage path, Power BI actions, tests, reconciliation
├─ Impact_Analysis.csv       the impact matrix for diff-friendly review
├─ Generated_SQL.sql         migration, updated procedure, updated views, reload call
├─ Rollback_Script.sql       original definitions restored and the column dropped
├─ Unit_Tests.sql            data quality suite annotated with expectations and sandbox results
├─ Integration_Tests.sql     before/after snapshot queries and reporting parity checks
├─ PowerBI_Change_Plan.md    dataset, measures, relationships, visuals and the TMDL column
├─ Deployment_Checklist.md   what is done, what is outstanding, what blocks release
├─ PR_Description.md         ready to paste into the pull request
├─ Release_Notes.md          what changed, deployment steps, validation performed
├─ Validation_Report.md/pdf  reconciliation table, test results, readiness verdict, agent log
└─ Run_Manifest.json         the whole run as structured data for downstream automation
```

## The ten agents

| # | Agent | What it does |
| --- | --- | --- |
| 1 | Request Intake | Parses the request into `{report, requested_column, business_reason}`, resolves the report against the catalog, and halts with clarification questions when the request is ambiguous. |
| 2 | Metadata Discovery | Resolves the business phrase to a physical column through the data dictionary, then the information schema, and attaches lineage, Jira history and existing documentation as evidence. |
| 3 | Impact Analysis | Walks the lineage graph in both directions to build the impact matrix and works out the join plan the attribute needs to reach the fact table. |
| 4 | SQL Change Generation | Edits the real procedure and view definitions, and emits the migration, the diffs and the matching rollback. |
| 5 | Documentation | Renders the requirement, technical design, PR description and release notes. |
| 6 | Unit Test Generation | Derives population, row count, null, duplicate, datatype, domain and source-to-target checks, then executes them. |
| 7 | Integration Testing | Snapshots the financial metrics, replays the ETL with the change applied and reconciles before against after. |
| 8 | Power BI Impact | Maps the change onto the dataset table, measures, relationships and visuals, and emits the TMDL column definition. |
| 9 | Deployment Readiness | Turns the evidence into a checklist and a blocking verdict. |
| 10 | Final Output | Re-renders every document with the test evidence and writes the change package. |

Agents share a `ChangeContext` and each one returns a typed artifact, so any agent can be swapped
for a different implementation without touching the others.

Each agent has a reference page in [`docs/jobs/`](docs/jobs/README.md) covering its context
contract, algorithm, halt conditions and tests. If you are reading the code — or pointing an AI
assistant at it — start with [`AGENTS.md`](AGENTS.md).

## How it decides what to change

Impact analysis is a graph traversal, not a lookup table. The catalog yields two kinds of edges:
**data** edges (staging → procedure → fact → view → dataflow → dataset → report) and **control**
edges (a Lambda invoking a procedure, a Step Function orchestrating a job). Given the requested
report, the agent walks upstream to find the fact table that feeds it, finds the procedure that
loads that fact table, and then asks how the requested attribute can reach that procedure:

- **existing join** — the procedure already joins the source table, so the attribute is projected
  from the existing alias;
- **new join** — the source table is reachable through a recorded relationship to a table the
  procedure already reads, so a `LEFT JOIN` is generated and the null check is downgraded to a
  warning because unmatched rows are now possible;
- **unreachable** — no relationship exists, so the run halts rather than guessing.

Objects between the fact table and the report are marked *Modify*; the dataflow and dataset are
marked *Refresh*; components on control edges are marked *Review*; other consumers of the fact
table are listed as reviewed-no-change so nothing is silently missed.

## Safety behaviours

These are the parts worth reviewing, because they encode judgement rather than mechanics.

- **Financial reconciliation gates the release.** Every monetary column on the impacted fact
  table, the row counts and the business key counts are compared before and after. Drift is a
  blocking failure, which is the control the RCM team asked for after a prior AR balance incident.
- **Aggregate views are never edited automatically.** Adding an attribute to a `GROUP BY` view
  changes its grain, so the view is flagged for a business decision and the reason is recorded in
  the design document.
- **Generated SQL must execute.** If the rewritten procedure or view does not run in the sandbox,
  the run halts with the database error instead of shipping a broken script.
- **Ambiguity stops the pipeline, but not the output.** An unknown report or an unresolvable
  column halts the run and still produces `Requirement.md` with the closest catalog matches, so
  the requester gets a question rather than silence.
- **Governance is explicit.** PII columns block the checklist until the audience is approved and
  uncertified columns raise a warning naming the data steward.
- **Every change has a rollback.** The original definitions are captured verbatim before editing.

## Repository layout

```
src/rcm_change_platform/
├─ agents/            the ten pipeline stages (a01_intake.py … a10_final_package.py)
├─ catalog/           metadata repository, lineage graph and the seeded RCM catalog
│  └─ seeds/          information schema, data dictionary, ETL, Power BI, Jira, docs, sample rows
├─ sandbox/           executable warehouse (SQLite) plus the baseline/candidate runner
├─ writers/           dependency-free xlsx and pdf writers
├─ sqlkit.py          structure aware SQL editing (projection, insert list, joins, diffs)
├─ rendering.py       markdown renderers for every document
├─ models.py          typed artifacts exchanged between agents
├─ context.py         shared pipeline state
├─ llm.py             optional LLM backing with a deterministic fallback
├─ orchestrator.py    pipeline execution, including the salvage path after a halt
└─ cli.py             the rcm-change command
```

The platform has **no runtime dependencies**; `pytest` is needed only to run the tests.

## The metadata catalog

The bundled catalog in `src/rcm_change_platform/catalog/seeds/` models a small but realistic RCM
warehouse: staging AR transactions, patient/payer/provider dimensions, an AR fact loaded by a
stored procedure, detail and aging-summary views, Glue/Lambda/Step Function components, the
`pb_ar_aging` dataset with measures and visuals, Jira history and standards documents.

Point the platform at exported metadata from your own environment with `--metadata-dir`, keeping
the same file names and shapes:

```bash
rcm-change run "Add Patient Financial Class to the AR Aging Report" --metadata-dir ./metadata
```

`docs/PRODUCTION_INTEGRATION.md` describes how to populate those files from Redshift, the Power BI
REST API, Glue and Jira, and which parts need a real connection rather than the sandbox.

## Inspecting the catalog

```bash
rcm-change catalog reports          # reports, datasets, tables, views, routines, etl, terms
rcm-change lineage rcm.fact_ar      # upstream and downstream objects
```

## Using an LLM

Every agent is deterministic by default, which keeps runs reproducible and tests hermetic. When a
provider is configured, intake uses it to parse unusual phrasing and metadata discovery uses it to
break ties between near-identical candidate columns; both fall back to the rule-based path if the
call fails or returns something unusable.

```bash
export ANTHROPIC_API_KEY=...        # or OPENAI_API_KEY
export RCM_LLM_MODEL=claude-sonnet-4-5
export RCM_LLM_PROVIDER=auto        # auto | anthropic | openai | none
```

## Python API

```python
from rcm_change_platform import RunOptions, run_change_request

context = run_change_request(
    "Add Patient Financial Class to the AR Aging Report",
    options=RunOptions(output_dir="out", execute_tests=True),
)

print(context.impact.names())                 # impacted objects
print(context.reconciliation.balanced)        # financial verdict
print(context.checklist.ready)                # release verdict
print(context.package.files)                  # artifacts written
```

## Tests

```bash
python -m pytest
```

The suite covers the catalog and lineage traversal, the SQL editing primitives, each agent, the
sandbox assertions, both writers, the LLM abstraction and two end-to-end scenarios: an attribute
that arrives through an existing join, and one that requires a new join. It also asserts the
failure paths — unresolvable columns, unreachable source tables, SQL that will not execute and a
change that silently drops rows.

## Scope

This is a working platform against a metadata catalog and a sandbox, not a production deployment
tool. It does not connect to Redshift, publish to Power BI, or open pull requests on its own; it
produces the artifacts a human reviews and a deployment job applies. `docs/PRODUCTION_INTEGRATION.md`
covers what each of those integrations requires, and `docs/REQUIREMENTS_TRACEABILITY.md` maps the
original requirement document to the implementation.

## Documentation

| Document | For |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | The entry point for developers and AI assistants: layout, invariants, where each change belongs |
| [`docs/jobs/`](docs/jobs/README.md) | One reference page per pipeline job, plus the shared contracts |
| [`docs/PRODUCTION_INTEGRATION.md`](docs/PRODUCTION_INTEGRATION.md) | Pointing the platform at a real environment |
| [`docs/REQUIREMENTS_TRACEABILITY.md`](docs/REQUIREMENTS_TRACEABILITY.md) | Original requirement mapped to the implementation |
