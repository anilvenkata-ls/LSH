# Job 5 — Documentation

`DocumentationAgent` · `src/rcm_change_platform/agents/a05_documentation.py` · step 5

## Purpose

Render the human-readable documents: the requirement record, the technical
design, the pull request description, the release notes and the validation
report. The job itself is thirty lines — all the work is in `rendering.py`.

Its position in the pipeline is the interesting part. It runs **before** the
tests, halfway through, so that a run which falls over later still has documents
to show. Job 10 renders them again once evidence exists.

## Contract

**Reads**

Everything written so far: `request`, `metadata`, `impact`, `change_set`, and
`options` for the release label and the execution mode. Each renderer handles
missing fields itself.

**Writes**

| To | Contents |
| --- | --- |
| `context.documents` | Five entries keyed by filename, each holding rendered markdown. |

Nothing is written to disk here. Job 10 owns the filesystem.

## The documents

| Key | Renderer | What it contains |
| --- | --- | --- |
| `Requirement.md` | `rendering.requirement` | The raw request, the structured requirement as JSON, the resolved column, the metadata evidence trail, related Jira history and documentation. |
| `Technical_Design.md` | `rendering.technical_design` | Source data, the data flow, the impact matrix, the generated diffs, risks and the rollback strategy. |
| `PR_Description.md` | `rendering.pr_description` | Impacted objects grouped by action, test evidence, the deployment verdict and a reviewer checklist. |
| `Release_Notes.md` | `rendering.release_notes` | What changed, deployment steps, validation performed, known impacts. |
| `Validation_Report.md` | `rendering.validation_report` | The reconciliation table, test results, the readiness verdict and the agent log. |

The first four are in the `DOCUMENT_BUILDERS` mapping; `Validation_Report.md` is
rendered separately in both `execute` and `refresh_documents`. It is the
validation report that also becomes a PDF in job 10.

## How it works

```python
for filename, builder in DOCUMENT_BUILDERS.items():
    context.documents[filename] = builder(context)
context.documents["Validation_Report.md"] = rendering.validation_report(context)
```

That is the whole job. The design constraint it depends on: **every renderer is
a pure function of the context.** No renderer mutates anything or caches, which
is what makes calling them a second time in job 10 safe and is why the
mid-pipeline render costs nothing but a few milliseconds.

`refresh_documents(context)` is exported from this module and called by job 10.
It is the same loop. Keeping it here rather than in job 10 means the set of
documents is defined in exactly one place.

## Rendering on the halt path

Every renderer opens with a guard and degrades rather than raising:

| Renderer | When its inputs are missing |
| --- | --- |
| `requirement` | *The request could not be parsed.* |
| `technical_design` | *The pipeline halted before a design could be produced.* |
| `pr_description` | *The pipeline halted before a change was produced.* |
| `release_notes` | *No change was produced.* |
| `validation_report` | Renders anyway, with whatever sections have data. |

`requirement` is the one that matters on a halt. When job 1 or job 2 stops the
run, this job is invoked by the salvage path and produces a requirement document
containing the clarification questions and the closest catalog matches — the
question the requester needs to answer.

## Halt conditions

None. This job must work when other things have not.

## Warnings

None.

## Key functions

| Function | Responsibility |
| --- | --- |
| `DocumentationAgent.execute` | Render all five documents into the context. |
| `refresh_documents` | The same, called by job 10 after the tests. |
| `DOCUMENT_BUILDERS` | Filename → renderer mapping; the registry for the first four. |
| `rendering._table`, `_bullets`, `_json_block`, `_timestamp` | Shared markdown helpers. |
| `rendering._test_summary` | Formats a `TestRun` into a sentence, distinguishing "not generated" from "generated, not executed". |

## Tests and extension points

Covered by `tests/test_agents_reporting_release.py`, including the degraded
output on the halt path.

When changing this job:

- **Add a document by adding to `DOCUMENT_BUILDERS`**, and nothing else. Job 10
  iterates `context.documents`, so a new entry is written to disk automatically.
  Job 9 checks three specific documents by filename for its checklist, so a new
  document does not affect the verdict unless you also change job 9.
- **Keep renderers pure.** A renderer that mutated the context would make the
  two render passes produce different results, and the mid-pipeline documents
  would stop being a faithful preview.
- **Handle `None` in a new renderer.** It will be called on the halt path, where
  most of the context is empty. Return a short explanatory document rather than
  raising — an exception here becomes a failed salvage and the user gets
  nothing.
- **The documents are the deliverable.** The reviewer reads these, not the run
  report. When a generated document reads badly, fix `rendering.py`; the
  renderers are the only place prose is produced.
