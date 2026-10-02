# Job 10 — Final Output

`FinalOutputAgent` · `src/rcm_change_platform/agents/a10_final_package.py` · step 10

## Purpose

Re-render every document now that test evidence exists, and write the change
package to disk. This is the only job that touches the filesystem, and the only
one that produces the non-markdown artifacts — the spreadsheet, the CSV, the PDF
and the run manifest.

It is also a salvage job: when an earlier job halts, the orchestrator runs this
one anyway, so the requester always receives a package.

## Contract

**Reads**

The whole context. Every field that exists becomes part of the package; every
field that does not is skipped rather than faked.

**Writes**

| To | Contents |
| --- | --- |
| `context.documents` | Re-rendered via `refresh_documents`. |
| `context.package` | A `ChangePackage` with the root path and the sorted list of filenames. |
| the filesystem | `<output_dir>/Change_Request/` with 15 artifacts in a healthy run. |

## How it works

1. **`refresh_documents(context)`** — re-render the five markdown documents, now
   that `unit_run`, `integration_run`, `reconciliation`, `power_bi` and
   `checklist` are populated. The versions job 5 produced are replaced.
2. **Create `<output_dir>/Change_Request/`**, `PACKAGE_DIRNAME` being the
   constant.
3. **Write every entry in `context.documents`** — the markdown files.
4. **Write the SQL**: `Generated_SQL.sql` from `deployment_script(context)`,
   `Rollback_Script.sql` from the change set, and the two test scripts.
5. **Write the Power BI plan and the checklist** as markdown, each only if the
   corresponding context field exists.
6. **Write the binary and structured artifacts**: the xlsx workbook, the impact
   CSV, the validation PDF and the run manifest.
7. **Record the package** in `context.package` with a sorted file list.

`_write_text` creates parent directories and guarantees a trailing newline, so
the artifacts are well-formed text files that diff cleanly.

## The artifacts

| File | Built from |
| --- | --- |
| `Requirement.md`, `Technical_Design.md`, `PR_Description.md`, `Release_Notes.md`, `Validation_Report.md` | `context.documents` after the refresh |
| `Generated_SQL.sql` | `deployment_script` — migration, each edited definition, the reload call |
| `Rollback_Script.sql` | `change_set.rollback_sql` |
| `Unit_Tests.sql` | `unit_suite` annotated with `unit_run` results |
| `Integration_Tests.sql` | `integration_suite` annotated with `integration_run` results |
| `PowerBI_Change_Plan.md` | `context.power_bi` |
| `Deployment_Checklist.md` | `context.checklist` |
| `Impact_Analysis.xlsx` | five sheets, below |
| `Impact_Analysis.csv` | the impact matrix only |
| `Validation_Report.pdf` | `Validation_Report.md` through `markdown_to_blocks` |
| `Run_Manifest.json` | the whole context |

### The test scripts carry their results

`_suite_sql` writes each case with its category, expectation, severity, sandbox
status and observed value as comments above the SQL:

```sql
-- [Null Validation] null_validation
-- Expectation: 0 records
-- Severity: blocking | Sandbox result: passed | observed: 0
SELECT COUNT(*) AS null_rows
FROM rcm.fact_ar
WHERE patient_financial_class IS NULL;
```

So the file is both the executable suite for the dev environment and the
evidence of what happened in the sandbox. Cases that were not executed say
`not executed` rather than silently omitting the line.

### The workbook

`Impact_Analysis.xlsx` has five sheets, written by the dependency-free writer in
`writers/xlsx.py`:

| Sheet | Rows |
| --- | --- |
| Impact Matrix | object, type, impact, layer, risk, owner, rationale |
| Lineage Path | the propagation path, numbered, with each object's type and layer |
| Power BI | the action list |
| Tests | both runs combined: suite, test, category, status, expectation, observed |
| Reconciliation | metric, before, after, delta, PASS/FAIL |

`Impact_Analysis.csv` holds the same rows as the first sheet, from the shared
`_impact_rows`, because a CSV diffs in code review and a spreadsheet does not.

### The manifest

`write_run_manifest` is a module-level function, not a method, because the
orchestrator calls it again after the pipeline finishes. It serialises every
artifact through `to_dict()`, plus the agent reports and the warnings.

The double write is deliberate: job 10 writes the manifest, but its own
`AgentReport` does not exist until `Agent.run` returns. `ChangePipeline.run`
rewrites it so the manifest contains all ten reports. This is why
`Run_Manifest.json` is the one artifact whose content differs between what this
job wrote and what ends up on disk.

The manifest is the machine-readable interface to a run. Downstream automation
should read it rather than parsing the markdown.

## Halt conditions

None. The job is a salvage job and must work when the pipeline has already gone
wrong. Every section is guarded on the corresponding context field existing, so
a run that halted in job 2 writes a package containing `Requirement.md` with the
clarification questions, degraded placeholders for the other documents, and a
manifest with mostly nulls.

An exception here would still be caught by `Agent.run` and recorded, but the
package would be incomplete — which is why the guards matter.

## Warnings

None.

## Key functions

| Function | Responsibility |
| --- | --- |
| `execute` | Refresh, create the directory, write everything, record the package. |
| `write_run_manifest` | Module-level; also called by the orchestrator. |
| `_write_text` | Write with a guaranteed trailing newline. |
| `_suite_sql` | Annotate a suite with its results as comments. |
| `_impact_rows` | The shared matrix rows for the sheet and the CSV. |
| `_write_impact_workbook` | The five sheets. |
| `_power_bi_markdown` / `_checklist_markdown` | Render the two late artifacts. |
| `writers.write_xlsx` / `write_pdf` / `markdown_to_blocks` | The dependency-free writers. |

## Tests and extension points

Covered by `tests/test_pipeline_end_to_end.py` (the package contents for both
join strategies and for a halted run) and `tests/test_writers.py` (xlsx and pdf
structure).

When changing this job:

- **Adding a markdown document belongs in job 5**, not here. This job iterates
  `context.documents`, so a new renderer registered there is written
  automatically.
- **Guard every new artifact** on the context field it needs. This job runs on
  the halt path, where most fields are `None`.
- **The writers have no dependencies and that is a constraint, not an
  accident.** `writers/xlsx.py` and `writers/pdf.py` exist so the package can
  declare `dependencies = []`. Reaching for `openpyxl` or `reportlab` to add a
  feature breaks the platform's install story — extend the writers instead.
- **Keep the manifest serialisable.** `Serializable.to_dict` handles nested
  dataclasses, enums, lists and datetimes. A field holding anything else fails
  here, at the very end of a run, which is the most expensive place to find out.
