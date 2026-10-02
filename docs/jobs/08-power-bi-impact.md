# Job 8 — Power BI Impact

`PowerBIImpactAgent` · `src/rcm_change_platform/agents/a08_power_bi.py` · step 8

## Purpose

Carry the warehouse change across into the semantic model: which dataset table
gains the column, which measures and relationships sit on that table, which
visuals are candidates for surfacing it, whether a refresh is required, and the
TMDL definition to apply.

Nothing is published. The output is a plan a human applies, because Power BI
changes involve visual layout decisions that the platform has no basis to make.

## Contract

**Reads**

| From | Used for |
| --- | --- |
| `context.request.report` | Finding the report in the Power BI metadata. |
| `context.metadata.column` | Column name, business term and data type. |
| `context.impact` | Which views were marked `Modify`, to find the dataset tables that source from them. |
| `context.repo` | Reports, datasets, measures, relationships, pages and visuals. |

**Writes**

| To | Contents |
| --- | --- |
| `context.power_bi` | A `PowerBIPlan`: dataset, report, workspace, action list, impacted measures, relationships and visuals, refresh flag, TMDL snippet. |
| `context.warnings` | When no dataset table sources from a modified view. |

## How it works

### 1. Join the two metadata graphs

The report names its dataset; the dataset's tables each name a `source`. The
link between the warehouse and Power BI is that **a dataset table's `source` is
a warehouse object name**, spelled identically. The job intersects the set of
views job 3 marked `Modify` with the dataset's table sources:

```python
modified_views = {item.object_name for item in impact.items
                  if item.action is ImpactAction.MODIFY and repo.view(item.object_name)}
target_tables = [t for t in dataset["tables"] if t["source"] in modified_views]
```

If that intersection is empty the job warns — the dataset probably uses a custom
M query rather than a plain view, so a human has to change the query by hand.
It does not halt: the rest of the plan is still useful.

### 2. Build the action list

For each target table, in this order:

| Action | Target type | Meaning |
| --- | --- | --- |
| Add column | `dataset_table` | Add the column from its source view to the table. |
| Refresh semantic model | `dataset` | Only when the storage mode is Import. |
| Validate | `measure` | Each measure on the modified table; confirm totals are unchanged after refresh. |
| Review field placement | `visual` | Each candidate visual, as `<page> / <id> (<type>)`. |
| Publish validation | `report` | Publish and compare totals against the pre-change snapshot. |

`refresh_required` is true when the dataset's `storage_mode` is `Import`
(case-insensitively, defaulting to Import when unset). DirectQuery models see
the new column without a refresh, so the item is omitted rather than stated and
ignored.

### 3. Decide which visuals are candidates

`_visual_uses_table` marks a visual relevant when either:

- any of its `columns`, `rows` or `axis` fields is a column of the modified
  table, or
- any of its `values` is a measure that sits on that table.

This is a *candidate* list, not an instruction. The platform knows which visuals
are built on the affected table; it has no way to know which one the analyst
wants the new field on. That judgement stays with the person applying the plan,
and the checklist item in job 9 for reviewing visuals is deliberately
non-blocking and marked as a manual step.

### 4. Emit the TMDL column

`_tmdl` produces the column definition for the semantic model:

```tmdl
table 'AR Detail'
	column patient_financial_class
		dataType: string
		sourceColumn: patient_financial_class
		displayName: Patient Financial Class
		summarizeBy: none
		isHidden: false
```

The SQL type is mapped through `_DAX_TYPES` — `VARCHAR`/`CHAR`/`TEXT` to
`string`, `NUMERIC`/`DECIMAL` to `decimal`, the integer family to `int64`,
`DATE`/`TIMESTAMP` to `dateTime`, `BOOLEAN` to `boolean` — with the base type
taken before any `(n)` and an unknown type falling back to `string`.
`summarizeBy` is `none` for string, dateTime and boolean columns and `sum`
otherwise, so adding a text attribute does not create a meaningless implicit
aggregation. `displayName` uses the business term from the data dictionary, so
the model shows "Patient Financial Class" rather than the physical name.

TMDL is emitted with literal tab indentation, which the format requires.

### 5. Deduplicate

Measures, relationships and visuals are deduplicated with `dict.fromkeys`,
preserving discovery order, since one measure can be reached through more than
one target table.

## Halt conditions

| Condition | Message | What the user should do |
| --- | --- | --- |
| Missing metadata or impact | *Power BI analysis requires the metadata document and impact matrix.* | Out-of-order pipeline; tests only. |
| Report absent from Power BI metadata | *Report '…' is not in the Power BI metadata.* | Add the report to `power_bi.json`. |

The second is close to unreachable in a normal run, because job 1 resolved the
report against the same repository. It fires when `power_bi.json` is internally
inconsistent — a report listed in one section and missing from another.

## Warnings

| Warning | Raised when |
| --- | --- |
| No table in dataset '…' sources from a modified view; the dataset may need a manual query change | The source intersection is empty. |

## Key functions

| Function | Responsibility |
| --- | --- |
| `execute` | Joins the graphs, builds the action list, deduplicates. |
| `_visual_uses_table` | The field-binding check that makes a visual a candidate. |
| `_tmdl` | The semantic model column definition. |
| `_DAX_TYPES` | SQL type to Power BI type mapping. |

## Tests and extension points

Covered by `tests/test_agents_reporting_release.py`.

When changing this job:

- **The join key is the object name.** Everything here depends on dataset table
  `source` values matching warehouse object names exactly. When wiring a real
  environment, that is the field to get right — see
  [`PRODUCTION_INTEGRATION.md`](../PRODUCTION_INTEGRATION.md).
- **Write-back is the obvious extension.** `PowerBIPlan` already carries the
  TMDL snippet; applying it through the XMLA endpoint or committing it to a TMDL
  repository would turn the manual step into a reviewable diff. That crosses the
  "nothing is deployed" line, so it needs a deliberate decision.
- **Keep the visual list advisory.** Promoting it from candidates to
  instructions would mean guessing at report layout, and a wrong guess is worse
  than a list.
- **Only datasets reached through modified views are considered.** A dataset
  that reads the fact table directly, without a view in between, produces no
  target tables and only the warning. If that becomes common, widen the
  intersection to include modified tables.
