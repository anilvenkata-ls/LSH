# Pipeline contracts

The machinery every job shares: the state object, the base class, the ordering,
and what happens when a job stops the run. Read this once; the ten job pages
assume it.

## `ChangeContext` — the shared state

Defined in `src/rcm_change_platform/context.py`. One instance is created per run
and passed to every job in turn. Jobs never call each other; they read fields
written upstream and assign their own.

### Inputs, set at creation

| Field | Type | Meaning |
| --- | --- | --- |
| `raw_request` | `str` | The sentence the user typed. |
| `repo` | `MetadataRepository` | The catalog façade: dictionary, information schema, ETL, Power BI, Jira, docs, sample rows. |
| `graph` | `LineageGraph` | Object-level lineage built from `repo` by `LineageGraph.build`. |
| `options` | `RunOptions` | Output directory, whether to execute tests, requester, reason, request id, release label. |
| `llm` | `LLMClient` | `NullLLM` unless a provider is configured. |
| `started_at` | `datetime` | UTC timestamp, used in rendered documents. |

### Artifacts, each written by exactly one job

| Field | Type | Written by |
| --- | --- | --- |
| `request` | `ChangeRequest` | 1 |
| `metadata` | `MetadataDocument` | 2 |
| `impact` | `ImpactMatrix` | 3 |
| `change_set` | `SqlChangeSet` | 4 |
| `documents` | `dict[str, str]` | 5, refreshed by 10 |
| `unit_suite` | `TestSuite` | 6 |
| `unit_run` | `TestRun` | 6 |
| `integration_suite` | `TestSuite` | 7 |
| `integration_run` | `TestRun` | 7 |
| `reconciliation` | `ReconciliationReport` | 7 |
| `power_bi` | `PowerBIPlan` | 8 |
| `checklist` | `DeploymentChecklist` | 9 |
| `package` | `ChangePackage` | 10 |

Every artifact field starts as `None`, so a job that depends on an upstream
artifact must check for `None` and halt rather than assume. That is the
"missing prerequisites" guard at the top of most `execute` methods.

### Run bookkeeping

| Field | Type | Meaning |
| --- | --- | --- |
| `reports` | `list[AgentReport]` | One entry per job that ran: step, status, summary, duration, warnings raised. Appended by `Agent.run`, not by the job. |
| `warnings` | `list[str]` | Deduplicated, via `context.warn(...)`. |
| `halted_by` | `str` | The name of the job that stopped the run; empty when the run is healthy. |
| `scratch` | `dict[str, Any]` | Short-lived resources, currently the two sandboxes. Anything here with a `close` method is closed by `release_resources`. |

`context.summary()` flattens the run into the dictionary the CLI prints for
`--json`.

### `RunOptions`

| Option | Default | CLI flag | Effect |
| --- | --- | --- | --- |
| `output_dir` | `out` | `--output` / `-o` | Parent of the `Change_Request/` package. |
| `execute_tests` | `True` | `--no-execute` inverts | When false, jobs 6 and 7 generate suites but mark every case skipped and never touch the sandbox. |
| `requested_by` | `business_user` | `--requested-by` | Recorded on the requirement. |
| `business_reason` | `""` | `--reason` | Overrides the reason parsed out of the sentence. |
| `request_id` | `""` | `--request-id` | Overrides the generated `CR-xxxxxxxx` id. |
| `release` | `""` | `--release` | Release label in the release notes. |

## `Agent` — the base class

Defined in `agents/base.py`. A job subclasses it, sets `name` and `step`, and
implements one method:

```python
class MyAgent(Agent):
    name = "my_agent"     # stable identifier, appears in reports and halts
    step = 11             # position in the printed run report

    def execute(self, context: ChangeContext) -> str:
        ...
        return "one line summary for the run report"
```

`Agent.run` is the part you do not override. It:

1. Starts a timer and records how many warnings existed before the job.
2. Calls `execute`.
3. Decides the status: `halted` if the job halted the run under its own name,
   otherwise `completed`.
4. Catches any exception, converts it into a halt attributed to this job, and
   sets the status to `failed`.
5. Appends an `AgentReport` carrying the step, status, summary, duration in
   milliseconds and the warnings this job added.

Because exceptions become halts, a job never crashes the pipeline — the run
report tells you which job failed and why, and the salvage path still produces a
package.

The return value of `execute` is a status line for a human reading the terminal,
not a machine-readable result. Put machine-readable output in the context.

## Ordering

`PIPELINE` in `agents/__init__.py` is the single source of truth for order:

```python
PIPELINE: tuple[type[Agent], ...] = (
    RequestIntakeAgent, MetadataDiscoveryAgent, ImpactAnalysisAgent,
    SqlChangeGenerationAgent, DocumentationAgent, UnitTestGenerationAgent,
    IntegrationTestingAgent, PowerBIImpactAgent, DeploymentReadinessAgent,
    FinalOutputAgent,
)
```

`ChangePipeline` accepts a different tuple, which is how tests run a subset.
The `step` attribute on each class is only used for display, so if you reorder
the tuple, renumber the `step` values to match or the printed report will lie.

## Halt and salvage

`context.halt(agent, reason)` sets `halted_by` and records the reason as a
warning. `ChangePipeline.run` checks `context.halted` after each job and breaks
out of the loop.

It then runs the salvage jobs that have not already executed:

```python
SALVAGE_AGENTS = (DocumentationAgent, FinalOutputAgent)
```

So a run that halts in job 2 still gets its documents rendered and a package
written — containing `Requirement.md` with the clarification questions and the
closest catalog matches. This is the difference between the user getting a
question and the user getting nothing.

Three details worth knowing:

- Salvage is skipped for a job that already ran, so documents are not rendered
  twice when the halt happens late in the pipeline.
- `write_run_manifest` is called again after the loop, so `Run_Manifest.json`
  includes the report of the packaging job itself.
- `release_resources()` runs in a `finally`, so sandbox connections are closed
  on the halt and exception paths too.

Salvage can be turned off with `ChangePipeline(salvage=False)`, which is useful
in tests that want to assert the raw halt behaviour.

## Artifacts in `models.py`

Every artifact is a dataclass mixing in `Serializable`, which provides
`to_dict()`. `_plain` walks nested dataclasses, enums, lists and datetimes so
the result is JSON-serialisable — this is what makes `Run_Manifest.json`
possible without a custom encoder. If you add a field holding a type `_plain`
does not understand, the manifest is where it will break.

The enums carry the vocabulary the whole pipeline shares:

| Enum | Values | Used for |
| --- | --- | --- |
| `ChangeType` | `add_column`, `unknown` | What job 1 decided the request is. Only `add_column` is automated. |
| `ImpactAction` | `Modify`, `Refresh`, `Redeploy`, `Review`, `No Change` | What job 3 says must happen to each object. |
| `Severity` | `blocking`, `warning`, `info` | Whether a failing test blocks the release. |
| `TestStatus` | `passed`, `failed`, `skipped`, `error` | Outcome of one test case. |

Two computed properties decide the run's verdict, so they are worth knowing by
name:

- `TestRun.passed` — true when every case either passed or is non-blocking. A
  failing `warning` case does not fail the run.
- `ReconciliationReport.balanced` — true when every line is within tolerance
  (default `0.01`). Job 9 turns this into a blocking checklist item.

## The LLM boundary

`llm.py` exposes an `LLMClient` protocol with `available()` and `complete()`.
`default_client()` reads `RCM_LLM_PROVIDER`, `ANTHROPIC_API_KEY`,
`OPENAI_API_KEY` and `RCM_LLM_MODEL`, and returns `NullLLM` when nothing is
configured.

Only two jobs consult it, both through `complete_json`, which returns `None`
rather than raising when the provider is absent, the call fails or the reply is
not parsable JSON:

- Job 1 for parsing unusual request phrasing.
- Job 2 for breaking ties between near-identical candidate columns.

The rule for any new LLM use is the same: the deterministic path must still
produce a correct answer, and a failed call must not change the outcome.
