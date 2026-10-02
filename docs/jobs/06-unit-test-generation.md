# Job 6 — Unit Test Generation

`UnitTestGenerationAgent` · `src/rcm_change_platform/agents/a06_unit_tests.py` · step 6

## Purpose

Derive a data quality suite for the new column from the catalog, then **execute
it**. Generated tests that nobody runs do not protect the AR balances, so this
job builds the candidate warehouse in the sandbox, applies the generated change,
replays the ETL and runs every case.

It is also, incidentally, the job that proves the generated SQL parses and
populates the column. SQL that fails to execute halts the pipeline here rather
than shipping to a reviewer.

## Contract

**Reads**

| From | Used for |
| --- | --- |
| `context.metadata.column` | Column name, data type, nullability, domain values, source table. |
| `context.impact` | Target fact table, join strategy, the views marked `Modify`. |
| `context.change_set` | Applied to the sandbox (via `runner.candidate`). |
| `context.repo` | Business keys, the loading procedure's inputs, relationships, sample rows. |
| `context.options.execute_tests` | Whether to run the suite at all. |

**Writes**

| To | Contents |
| --- | --- |
| `context.unit_suite` | A `TestSuite` of up to eight cases, named `unit_tests_<column>`. |
| `context.unit_run` | A `TestRun` with one `TestResult` per case. |
| `context.scratch` | The candidate sandbox, reused by job 7 and closed by `release_resources`. |
| `context.warnings` | Names of failing cases. |

## The cases

Each case is generated only when the catalog supports it, so the suite adapts to
the column and the warehouse. Against the bundled catalog, all eight are
produced.

| Case | Category | Generated when | Asserts |
| --- | --- | --- | --- |
| `column_population` | Column Population | always | At least one row has a non-null value. |
| `null_validation` | Null Validation | always | See below — the severity depends on the join strategy. |
| `row_count_validation` | Row Count Validation | a driving table is identifiable | The fact table's row count equals the source's. |
| `duplicate_validation` | Duplicate Validation | the fact table declares `business_keys` | No business key appears twice. |
| `datatype_validation` | Data Type Validation | the type is `VARCHAR(n)` or `CHAR(n)` | No value exceeds `n` characters. |
| `domain_validation` | Domain Validation | the dictionary term lists `domain_values` | No value outside the certified domain. |
| `source_to_target_parity` | Source to Target Validation | a relationship links fact and source | The denormalised value equals the source dimension's. |
| `view_exposure_<view>` | Reporting Layer Exposure | one per view marked `Modify` | The view compiles and exposes the column. |

### The null check adapts to the join strategy

This is the judgement call in the job. The column is treated as nullable if the
source column is nullable **or** the join plan is `new_join`:

| Situation | Expectation | Severity |
| --- | --- | --- |
| Non-nullable source reached through an existing join | 0 nulls | `blocking` |
| Nullable source, or reached through a `LEFT JOIN` | nulls reported for review | `warning` |

A `LEFT JOIN` legitimately produces nulls for unmatched rows, so asserting zero
would fail the release for the wrong reason. The count is still reported — the
case runs and its observed value appears in `Unit_Tests.sql` — it just does not
block. `TestRun.passed` ignores non-blocking failures, which is the mechanism.

### The driving table

`_driving_table` picks the first input of the loading procedure whose layer is
`staging`, falling back to its first input. The row count comparison is only
meaningful against the table that drives the load's grain, which for a snapshot
load is the staging table.

## Execution

| Mode | Behaviour |
| --- | --- |
| `execute_tests=True` (default) | `runner.candidate(context)` builds the sandbox, applies the change set, replays the ETL; every case runs. |
| `execute_tests=False` (`--no-execute`) | The suite is generated, every case is marked `skipped` with the reason `execution disabled`, and `TestRun.executed` is `False`. |

`runner.candidate` caches the sandbox in `context.scratch`, so job 7 reuses the
same instance rather than rebuilding it.

### What the sandbox is

`WarehouseSandbox` (`sandbox/warehouse.py`) materialises the catalog into an
in-memory SQLite database: creates every table, seeds the sample rows, creates
every view, then executes the stored procedure bodies statement by statement as
the ETL. SQLite has no schemas or stored procedures, so `translate` rewrites
qualified names like `rcm.fact_ar` into quoted identifiers and maps a few
Redshift constructs (`GETDATE()`, `CREATE OR REPLACE VIEW`).

Assertions are declarative. Each `TestCase` carries an `assertion` dict that the
sandbox interprets:

| Kind | Meaning |
| --- | --- |
| `scalar` | Compare the first value of the result against `expected`. |
| `compare_scalar` | Run `expected_sql` too, compare the two scalars. |
| `empty` | Pass when the query returns no rows. |

with an `operator` of `eq`, `ne`, `gt`, `gte`, `lt` or `lte` and an optional
`tolerance`. This is why the SQL that ships in `Unit_Tests.sql` is exactly the
SQL that was executed — there is no second, hidden implementation of a check.

## Halt conditions

| Condition | Message | What the user should do |
| --- | --- | --- |
| Missing metadata or impact | *Unit test generation requires the metadata document and impact matrix.* | Out-of-order pipeline; tests only. |
| Sandbox execution fails | *Generated SQL failed to execute in the sandbox: …* | Read the database error in the message; the generated SQL or the catalog definition is wrong. |

The second is the pipeline's guarantee that generated SQL compiles. A
`SandboxError` carries the SQLite error and the first 400 characters of the
offending statement.

A test that *fails* does not halt. Failures are recorded, warned about, and
turned into a blocking checklist item by job 9 — the run continues so the
reviewer gets the full picture.

## Warnings

| Warning | Raised when |
| --- | --- |
| `Unit test failures: <names>` | One or more cases have status `failed`. |

## Key functions

| Function | Responsibility |
| --- | --- |
| `execute` | Build the suite, run it, summarise. |
| `_build_suite` | All eight case generators and the nullability decision. |
| `_driving_table` | Pick the staging input of the loader. |
| `_source_parity_case` | Build the fact-to-dimension comparison from the recorded relationship. |
| `_varchar_length` | Extract `n` from `VARCHAR(n)`. |
| `runner.candidate` | Build (and cache) the changed warehouse. |
| `WarehouseSandbox.run_cases` / `run_case` | Execute and evaluate. |
| `skipped_results` | Mark a whole suite skipped with a reason. |

## Tests and extension points

Covered by `tests/test_agents_testing.py` (case generation, the nullable
downgrade, the skip path) and `tests/test_sandbox.py` (the sandbox itself,
including SQL that will not execute and a change that silently drops rows).

When changing this job:

- **A new case needs a declarative assertion.** If you cannot express the check
  as one of the three assertion kinds, extend `WarehouseSandbox._evaluate`
  rather than evaluating it in the job — otherwise the SQL in `Unit_Tests.sql`
  stops matching what ran.
- **Guard every case on catalog support.** A case that assumes a field exists
  will crash on a sparse real-world catalog. The existing cases all check first,
  which is why the suite is "up to eight" rather than always eight.
- **Severity is the lever, not deletion.** When a check is legitimately noisy in
  some situation, downgrade it to `warning` so it still reports, as the null
  check does. Removing the case loses the observation.
- **The sandbox proves compilation and small-data behaviour, not production
  behaviour.** It is SQLite with a few dozen seeded rows. For a real
  environment, run `Unit_Tests.sql` where the data is — see
  [`PRODUCTION_INTEGRATION.md`](../PRODUCTION_INTEGRATION.md).
