# Requirements traceability

Maps the original requirement document for the *AI-Powered RCM Data Engineering Change Automation
Platform* to the implementation, and records where the implementation deliberately differs.

## Agents

| Requirement | Implementation | Tests |
| --- | --- | --- |
| Agent 1 – Request Intake: natural language in, structured requirement out | `agents/a01_intake.py`; regex grammar for the common request shapes, optional LLM extraction, report resolved against the catalog, clarification questions on ambiguity | `tests/test_agents_intake_metadata.py`, `tests/test_llm.py` |
| Agent 2 – Metadata Discovery: data dictionary, information schema, catalog, lineage, Power BI metadata, Jira, documentation | `agents/a02_metadata_discovery.py`; dictionary first with an information-schema fallback, every source recorded as `MetadataEvidence` | `tests/test_agents_intake_metadata.py` |
| Agent 3 – Impact Analysis: tables, views, procedures, Glue/Lambda/Step Functions, datasets, reports, measures, dataflows | `agents/a03_impact_analysis.py` over `catalog/lineage.py`; data and control edges, impact matrix, join plan | `tests/test_agents_impact_sql.py`, `tests/test_catalog.py` |
| Agent 4 – SQL Change Generation: updated SQL, updated procedure, migration, rollback | `agents/a04_sql_generation.py` with `sqlkit.py`; real definitions edited in place, unified diffs, rollback restores the originals | `tests/test_agents_impact_sql.py`, `tests/test_sqlkit.py` |
| Agent 5 – Documentation and Git: technical design, PR description | `agents/a05_documentation.py` with `rendering.py`; also requirement, release notes and validation report | `tests/test_agents_reporting_release.py` |
| Agent 6 – Unit Test Generation: population, row count, null, duplicate, datatype validation | `agents/a06_unit_tests.py`; adds domain and source-to-target parity checks, and executes them | `tests/test_agents_testing.py` |
| Agent 7 – Integration Testing: before/after snapshots, financial reconciliation of charges, payments, adjustments, denials, AR balances | `agents/a07_integration_tests.py` with `sandbox/runner.py`; metrics derived from the catalog, not hard coded | `tests/test_agents_testing.py` |
| Agent 8 – Power BI Impact: dataset, measures, relationships, pages, visuals | `agents/a08_power_bi.py`; emits the action list plus a TMDL column definition | `tests/test_agents_reporting_release.py` |
| Agent 9 – Deployment Readiness: development, testing, documentation checklist | `agents/a09_deployment_readiness.py`; adds reporting and governance sections, derives every item from evidence and produces a blocking verdict | `tests/test_agents_reporting_release.py` |
| Agent 10 – Final Output: the `Change_Request/` package | `agents/a10_final_package.py`; every requested artifact plus a Power BI plan, a checklist and a run manifest | `tests/test_pipeline_end_to_end.py` |

## Deliverables

| Requested file | Produced | Notes |
| --- | --- | --- |
| `Requirement.md` | yes | Structured requirement, resolved source column, metadata evidence, related Jira history |
| `Impact_Analysis.xlsx` | yes | Sheets: Impact Matrix, Lineage Path, Power BI, Tests, Reconciliation. A CSV of the matrix is written alongside it |
| `Generated_SQL.sql` | yes | Migration, updated procedure, updated views, reload call, in execution order |
| `Unit_Tests.sql` | yes | Each case annotated with its expectation, severity and sandbox result |
| `Integration_Tests.sql` | yes | Before/after snapshot queries and reporting parity checks |
| `PR_Description.md` | yes | Impacted objects grouped by action, test evidence, deployment verdict, reviewer checklist |
| `Release_Notes.md` | yes | What changed, deployment steps, validation performed, known impacts |
| `Rollback_Script.sql` | yes | Original definitions restored, then the column dropped |
| `Validation_Report.pdf` | yes | Rendered from `Validation_Report.md` by a dependency-free PDF writer |
| — | `Technical_Design.md` | Required by the document body but absent from the folder listing |
| — | `PowerBI_Change_Plan.md`, `Deployment_Checklist.md`, `Run_Manifest.json` | Added: the Power BI actions and the readiness verdict are useful as standalone files, and the manifest makes the run consumable by other automation |

## Deliberate differences

**Aggregate views are flagged, not edited.** The requirement implies every impacted view is
modified. Adding an attribute to a `GROUP BY` view changes its grain and therefore its row counts,
which is a business decision. `rcm.vw_ar_aging_summary` is marked *Review* with the reason
recorded in the design document.

**The null test adapts to the join strategy.** The requirement specifies "0 records" for the null
check. That holds when the attribute arrives through an existing inner join. When a `LEFT JOIN` is
required, nulls are legitimate, so the check is downgraded to a warning that reports the count
rather than failing the release for the wrong reason.

**Tests are executed, not only generated.** Generated tests that nobody runs do not protect the
AR balances, so the platform materialises the catalog in SQLite, applies the change, replays the
ETL and runs the suite. This is also what proves the generated SQL parses and populates the
column.

**Deployment readiness is derived, not asserted.** The requirement shows a checklist of green
ticks. Here an item is only complete if the evidence exists: tests that were generated but not
executed leave the item outstanding and block the verdict.

**The platform prepares deployments; it does not perform them.** No agent connects to Redshift,
publishes a Power BI dataset or opens a pull request. Those integrations are described in
`PRODUCTION_INTEGRATION.md`; the boundary keeps a human in the approval path, which matches the
future-vision section of the requirement.

## Success metrics

The requirement targets an 80% reduction in analysis effort and 70% in development effort. Those
are measured against real tickets, not asserted by the code. What the platform contributes is the
mechanism: impact analysis and test generation that used to be manual are now produced in one
run, consistently, with the evidence trail attached. Measure the reduction by running the platform
alongside the next few AR enhancement tickets and comparing logged effort.
