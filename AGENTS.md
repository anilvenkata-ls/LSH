# AGENTS.md — orientation for AI assistants and new developers

This file is the entry point. It tells you what this repository is, where each
kind of change belongs, and the rules a change must not break. Read it before
editing anything; then read the page for the specific job you are touching in
[`docs/jobs/`](docs/jobs/README.md).

## What this repository is

One Python package, `rcm_change_platform`, that turns a plain English request
from a business analyst —

> Add Patient Financial Class to the AR Aging Report

— into a reviewable change package for a healthcare revenue cycle management
(RCM) data warehouse: impact analysis, generated SQL, executed tests, a Power BI
change plan, documentation and a deployment verdict.

The work is split into **ten jobs** that run in a fixed order and share one
mutable object. Each job is a class in `src/rcm_change_platform/agents/`. The
jobs are the unit of understanding in this codebase — if you are trying to find
where something happens, start from the job table below, not from a file search.

| # | Job | Class | File | One line |
| --- | --- | --- | --- | --- |
| 1 | Request Intake | `RequestIntakeAgent` | `agents/a01_intake.py` | Parse the sentence into a structured request and resolve the report. |
| 2 | Metadata Discovery | `MetadataDiscoveryAgent` | `agents/a02_metadata_discovery.py` | Resolve the business phrase to a physical column, with an evidence trail. |
| 3 | Impact Analysis | `ImpactAnalysisAgent` | `agents/a03_impact_analysis.py` | Walk the lineage graph to build the impact matrix and the join plan. |
| 4 | SQL Change Generation | `SqlChangeGenerationAgent` | `agents/a04_sql_generation.py` | Edit the real procedure and view definitions; emit migration and rollback. |
| 5 | Documentation | `DocumentationAgent` | `agents/a05_documentation.py` | Render the requirement, design, PR description and release notes. |
| 6 | Unit Test Generation | `UnitTestGenerationAgent` | `agents/a06_unit_tests.py` | Derive the data quality suite and execute it in the sandbox. |
| 7 | Integration Testing | `IntegrationTestingAgent` | `agents/a07_integration_tests.py` | Replay the ETL before and after; reconcile the financial totals. |
| 8 | Power BI Impact | `PowerBIImpactAgent` | `agents/a08_power_bi.py` | Map the change onto the semantic model and emit the TMDL column. |
| 9 | Deployment Readiness | `DeploymentReadinessAgent` | `agents/a09_deployment_readiness.py` | Turn the evidence into a checklist and a blocking verdict. |
| 10 | Final Output | `FinalOutputAgent` | `agents/a10_final_package.py` | Re-render everything with test evidence and write the package to disk. |

Each job has a reference page under [`docs/jobs/`](docs/jobs/README.md) covering
its context contract, algorithm, halt conditions and tests.

## Repository map

```
src/rcm_change_platform/
├─ agents/            the ten jobs, plus base.py (the Agent contract)
├─ catalog/           metadata repository and lineage graph
│  └─ seeds/          the bundled RCM catalog as JSON
├─ sandbox/           SQLite warehouse (warehouse.py) and baseline/candidate builders (runner.py)
├─ writers/           dependency-free xlsx and pdf writers
├─ context.py         ChangeContext: the shared state every job reads and writes
├─ models.py          the typed artifacts jobs exchange
├─ orchestrator.py    runs the jobs in order; owns the halt/salvage behaviour
├─ sqlkit.py          structure aware SQL editing (projection, insert list, joins, diffs)
├─ rendering.py       markdown renderers, pure functions of the context
├─ llm.py             optional LLM backing with a deterministic fallback
├─ text.py            fuzzy matching of business language to physical metadata
└─ cli.py             the rcm-change command
```

`tests/` mirrors this layout. `docs/` holds the written documentation;
`examples/` holds a committed sample output package.

## How a run actually flows

1. `cli.main` builds a `MetadataRepository` (bundled seeds, or `--metadata-dir`)
   and calls `orchestrator.run_change_request`.
2. `ChangeContext.create` loads the repository, builds the `LineageGraph` and
   picks an LLM client (`NullLLM` unless a key is configured).
3. `ChangePipeline.run` calls each job in `agents.PIPELINE` order. Every job
   gets the same `ChangeContext`, reads what upstream jobs produced and assigns
   its own output to a named field.
4. If a job calls `context.halt(...)`, the loop stops. The orchestrator then
   runs the **salvage** jobs — Documentation and Final Output — so the requester
   still receives the evidence gathered so far and the clarification question,
   rather than a silent failure.
5. `context.release_resources()` closes the sandbox connections in a `finally`,
   so it runs on the halt path too.

The exit code is the contract with CI: `0` deployment ready, `1` checklist
blocked, `2` a job halted and a human must answer something.

## Rules a change must not break

These encode judgement the RCM team asked for. If your change would violate one,
that is a discussion, not a refactor.

- **Jobs communicate only through `ChangeContext`.** No job imports another job
  to call it. If you need a value, read the field the producing job wrote. This
  is what allows any job to be swapped for an LLM-backed implementation.
- **Zero runtime dependencies.** `pyproject.toml` declares `dependencies = []`
  and the xlsx and pdf writers exist precisely so that stays true. `pytest` is a
  dev dependency only. Do not add a package to make something convenient.
- **Deterministic by default.** With no API key the pipeline produces identical
  artifacts for identical input. Tests are hermetic — `conftest.py` forces
  `RCM_LLM_PROVIDER=none`. Any LLM call must have a deterministic fallback and
  must not change behaviour when the call fails.
- **Financial reconciliation gates the release.** Charges, payments,
  adjustments, denials, AR balances, row counts and business key counts are
  compared before and after. Drift is a blocking failure, never a warning.
- **Aggregate views are flagged, never edited.** Adding a column to a `GROUP BY`
  view changes its grain, so job 3 marks it *Review* and records why.
- **Generated SQL must execute.** Job 6 runs the change in the sandbox; SQL that
  does not run halts the pipeline instead of shipping.
- **Halt rather than guess.** An unknown report, an unresolvable column or an
  unreachable source table stops the run with a question. Every halt still
  produces `Requirement.md`.
- **Nothing is deployed.** No job connects to Redshift, publishes to Power BI or
  opens a pull request. The platform prepares a change for a human reviewer.

## Where to make which change

| You want to | Change this | Also update |
| --- | --- | --- |
| Change how a job behaves | the job's file in `agents/` | its page in `docs/jobs/`, its tests |
| Add a field two jobs share | `models.py`, then `context.py` | `docs/jobs/pipeline-contracts.md` |
| Add or reorder a job | `agents/__init__.py` `PIPELINE` | `docs/jobs/README.md`, `AGENTS.md` table |
| Change what the catalog exposes | `catalog/repository.py` | `docs/PRODUCTION_INTEGRATION.md` |
| Change how lineage edges are built | `catalog/lineage.py` | `docs/jobs/03-impact-analysis.md` |
| Edit SQL more cleverly | `sqlkit.py` | `tests/test_sqlkit.py` |
| Change a generated document | `rendering.py` | `docs/jobs/05-documentation.md` |
| Add a CLI flag | `cli.py` and `RunOptions` in `context.py` | `README.md` |

## Conventions

- Python 3.10+, `from __future__ import annotations` at the top of every module,
  modern type hints (`str | None`, `list[str]`).
- Module docstrings explain the module's responsibility and the judgement behind
  it. Keep that style: say *why*, not *what*.
- Jobs implement `execute(context) -> str` and return a one line summary for the
  run report. Never override `run`; the base class owns timing, status and
  exception capture.
- Artifacts in `models.py` are frozen-ish dataclasses with a `to_dict` from the
  `Serializable` mixin, so the run manifest stays JSON-serialisable.
- Catalog object names are fully qualified (`rcm.fact_ar`) and are the join key
  between the warehouse metadata and the Power BI metadata. Do not normalise
  them.

## Running things

```bash
pip install -e .                 # no runtime dependencies
pip install pytest

python -m pytest                 # 115 tests, under a second

rcm-change run "Add Patient Financial Class to the AR Aging Report" -o out
rcm-change catalog reports       # reports|datasets|tables|views|routines|etl|terms
rcm-change lineage rcm.fact_ar
```

To exercise one job in isolation, use the `run_agents` fixture in
`tests/conftest.py`, which runs a prefix of the pipeline and returns the context:

```python
def test_something(run_agents):
    context = run_agents((RequestIntakeAgent, MetadataDiscoveryAgent))
    assert context.metadata.column.physical_column == "patient_financial_class"
```

## Further reading

- [`docs/jobs/README.md`](docs/jobs/README.md) — the ten jobs in detail.
- [`docs/jobs/pipeline-contracts.md`](docs/jobs/pipeline-contracts.md) — the
  `ChangeContext` field table, the `Agent` base class, halt and salvage.
- [`docs/PRODUCTION_INTEGRATION.md`](docs/PRODUCTION_INTEGRATION.md) — pointing
  the platform at a real environment.
- [`docs/REQUIREMENTS_TRACEABILITY.md`](docs/REQUIREMENTS_TRACEABILITY.md) —
  original requirement mapped to implementation, and the deliberate differences.
- [`README.md`](README.md) — the product-level overview.
