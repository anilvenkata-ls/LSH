# Job 3 — Impact Analysis

`ImpactAnalysisAgent` · `src/rcm_change_platform/agents/a03_impact_analysis.py` · step 3

## Purpose

Work out everything the change touches, and how the new attribute physically
reaches the report. The output is two things: the impact matrix that the
spreadsheet and the design document are built from, and the **join plan** that
job 4 needs in order to edit the loading procedure. This is the most
consequential job in the pipeline — an object missing from the matrix is an
object nobody reviews.

Impact is computed by traversing the lineage graph, not by looking anything up
in a table. That is why adding an object to the catalog is enough to make it
appear in future analyses.

## Contract

**Reads**

| From | Used for |
| --- | --- |
| `context.request` | The target report. |
| `context.metadata.column` | The source table and physical column. |
| `context.graph` | Upstream and downstream traversal, over both edge kinds. |
| `context.repo` | Object types, layers, owners, view definitions, routines, relationships. |

**Writes**

| To | Contents |
| --- | --- |
| `context.impact` | An `ImpactMatrix`: items, propagation path, report, source table, target fact table, join plan, warnings. |

## The lineage graph

Built once per run by `LineageGraph.build` (`catalog/lineage.py`) from the
repository. Two kinds of edge, and the distinction drives the whole analysis:

- **`DATA`** — values physically flow along it: a routine reads a table, a
  routine writes a table, a view selects from an object, a dataflow stages a
  source, a dataset imports a source, a report renders a dataset.
- **`CONTROL`** — orchestration, with no column flowing: a Lambda calls a
  procedure, a Lambda refreshes a dataset, a Step Function orchestrates another
  component.

Traversal defaults to `DATA` only. Control edges are followed separately, which
is how ETL components get marked *Review* rather than *Modify*.

Note the direction of control edges: they run from the thing being operated on
*to* the operator (`rcm.sp_load_ar_fact → lambda_run_ar_load`), so walking
outgoing control edges from a changed object finds its callers.

## How it works

### 1. Find the fact table

Walk `DATA` edges upstream from the report to get its ancestors, keep those the
repository marks with `layer == "fact"`, and pick the one closest to the report
by shortest-path length. A report with no fact ancestor halts.

### 2. Find the loading procedure

`repo.routines_writing(fact_table)` gives the procedures that write it; the
first is the loader. No loader halts, because there is nothing to edit.

### 3. Build the join plan

`_join_plan` decides how the loader can reach `source_table.column`, and returns
one of three strategies:

| Strategy | When | What job 4 does with it |
| --- | --- | --- |
| `existing_join` | The loader already reads the source table | Projects `<existing alias>.<column>`; no join added. |
| `new_join` | A relationship links the source table to a table the loader already reads | Adds the generated `LEFT JOIN` and projects through the new alias. |
| `unreachable` | No relationship found | Nothing — the job halts first. |

For `new_join` the clause is built from the recorded relationship, with the
column order flipped as needed depending on which side of the relationship the
source table sits on, and a fresh alias from `sqlkit.suggest_alias` so it cannot
collide with an alias already in the procedure.

Choosing `LEFT JOIN` rather than an inner join is deliberate: an inner join
would silently drop fact rows with no matching dimension row, which would move
the financial totals and fail job 7. The cost is that nulls become possible,
which is why job 6 downgrades its null check to a warning under this strategy.

### 4. Classify every object

| Objects | Action | Why |
| --- | --- | --- |
| The source table | `No Change` | It provides the attribute; nothing about it changes. |
| The fact table | `Modify` (risk medium) | Gains the column. If the column already exists it is `No Change` and a warning is raised. |
| The loading procedure | `Modify` (risk medium) | Must populate the column in its INSERT and SELECT lists. |
| Non-aggregate views on the path | `Modify` | Expose the column to the reporting layer. |
| Aggregate views on the path | `Review` (risk medium) | See below. |
| Dataflows on the path | `Refresh` | Reload so the column lands in the dataset. |
| Datasets on the path | `Refresh` (risk medium) | Refresh the semantic model. |
| The report | `Modify` | Surface the column on the visuals. |
| Components reachable over control edges | `Review` | Confirm the orchestration still succeeds. |
| Other consumers of the fact table | `Review` | The change is additive, so no edit is expected — but nothing is silently missed. |

"On the path" means downstream of the fact table *and* an ancestor of the
report. Objects downstream of the fact table that do not feed this report are
other consumers, which is what keeps an unrelated dashboard out of the matrix.

**Aggregate views are never edited automatically.** A view whose definition
contains `GROUP BY` would change grain if a column were added to it, and that
changes its row counts — a business decision, not a mechanical edit. The view is
marked `Review`, the reason is recorded in the matrix warnings, and it reaches
the design document from there.

Control edges are followed **transitively** with a queue, starting from the
loader, the fact table and every on-path object. That is why the Step Function
that orchestrates the Lambda that calls the procedure appears in the matrix,
two hops from anything that actually changed.

### 5. Record the propagation path

Not the shortest path. A dimension often reaches a report twice — directly,
because a reporting view joins it, and indirectly through the fact load — and
the shortest path would describe the route the change does *not* take. So the
path is anchored on the loader and the fact table:

```
source table → loader → fact table → … shortest path to the report …
```

## Halt conditions

| Condition | Message | What the user should do |
| --- | --- | --- |
| Missing request or column | *Impact analysis requires a resolved request and column.* | Out-of-order pipeline; tests only. |
| No fact table | *No fact table feeding '…' was found in the lineage graph.* | Check `layer` on the tables and the view/dataset `depends_on` and `sources` lists. |
| No loading procedure | *No stored procedure loads …; cannot automate the change.* | Populate `routines[].writes` in `information_schema.json`. |
| Source not joinable | *… is not joinable to the inputs of … using the recorded relationships.* | Declare the relationship in `information_schema.json`. |

The last one is the common failure in a real environment. Redshift does not
enforce foreign keys, so `relationships` has to be curated or mined from the
join predicates in the procedure bodies — see
[`PRODUCTION_INTEGRATION.md`](../PRODUCTION_INTEGRATION.md).

## Warnings

| Warning | Raised when |
| --- | --- |
| `<fact>.<column>` already exists; the migration will be skipped | The fact table already has the column. |
| `<view>` aggregates rows; `<column>` was deliberately not added | An aggregate view sits on the path. |
| `<source>` is not joinable to the inputs of `<loader>` | Also the halt reason for the unreachable strategy. |

These are copied into `change_set.notes` by job 4, so they surface in the
generated SQL and the design document.

## Key functions

| Function | Responsibility |
| --- | --- |
| `execute` | Sequences the five stages and owns the halts. |
| `_target_fact_table` | Nearest fact-layer ancestor of the report. |
| `_loading_routine` | First routine writing the fact table. |
| `_join_plan` | The three-way strategy decision. |
| `_add_warehouse_items` | Fact table, loader, and the aggregate-view judgement. |
| `_add_etl_items` | Transitive control-edge walk. |
| `_add_review_items` | Other consumers of the fact table. |
| `_propagation_path` | The loader-anchored path. |
| `graph.upstream` / `downstream` / `shortest_path` | BFS over the chosen edge kinds. |

## Tests and extension points

Covered by `tests/test_agents_impact_sql.py` (matrix contents, the aggregate-view
rule, unrelated reports excluded, transitive control edges) and
`tests/test_catalog.py` (graph construction and traversal).

When changing this job:

- **Lineage is object-level, not column-level.** A view that selects from the
  fact table is marked `Modify` whether or not it would actually reference the
  new column. Column-level edges are the single highest-value extension to the
  platform; they would need `depends_on` to carry column mappings.
- **Risk levels are assigned, not computed.** `medium` on the fact table, the
  loader, aggregate views and datasets; `low` elsewhere. They are advisory
  inputs to a reviewer.
- **`No Change` items are not noise.** Listing the source table and the
  unaffected consumers is what lets a reviewer confirm the analysis considered
  them. Do not filter them out of the matrix.
- **Adding a new object type** means teaching `repo.object_type` and
  `repo.layer_of` about it as well, or it lands in the matrix as `unknown`.
