# Job 4 — SQL Change Generation

`SqlChangeGenerationAgent` · `src/rcm_change_platform/agents/a04_sql_generation.py` · step 4

## Purpose

Produce the SQL that implements the change: the migration that adds the column,
the edited stored procedure and views, and a rollback that restores exactly what
was there before.

The important property is that the edits are applied **to the real definitions
from the catalog**, not regenerated from a template. A reviewer reads a unified
diff of a procedure they recognise, with their own formatting and comments
intact, which is the difference between a change that gets approved and one that
gets rewritten by hand.

## Contract

**Reads**

| From | Used for |
| --- | --- |
| `context.metadata.column` | Physical column name and data type. |
| `context.impact` | Which objects are `Modify`, the target fact table, and the join plan. |
| `context.repo` | The current procedure bodies and view definitions. |
| `context.request` | Request id and raw text, for the script headers. |

**Writes**

| To | Contents |
| --- | --- |
| `context.change_set` | A `SqlChangeSet`: migration SQL, rollback SQL, one `ObjectChange` per edited object, target table and column, notes. |

Each `ObjectChange` carries `before`, `after`, a unified `diff` and a one-line
`summary`. Job 6's sandbox applies the `after` definitions; the rollback script
is assembled from the `before` ones.

## How it works

1. **Decide whether a migration is needed.** If the fact table already has the
   column, no `ALTER TABLE` is produced and a note records why. Otherwise
   `_migration` emits the `ALTER TABLE … ADD COLUMN` plus a commented backfill
   hint naming the loading procedure.
2. **Edit each `Modify` object** from the impact matrix, dispatching on object
   type. Anything that is neither a stored procedure nor a view — the report, for
   instance — is skipped here; it is not SQL.
3. **Build the rollback** from what was generated.
4. **Copy the impact warnings** into `change_set.notes`, so the reasons objects
   were skipped travel with the SQL.

### Editing a stored procedure

`_procedure_change` applies up to three edits in a fixed order, via `sqlkit`:

1. If the join plan says `new_join`, add the generated `LEFT JOIN` to the FROM
   clause with `sqlkit.add_join`.
2. Add the column to the INSERT column list with `sqlkit.add_insert_column`.
3. Add the join plan's expression — `p.patient_financial_class`, aliased per the
   plan — to the SELECT projection with `sqlkit.add_projection_column`.

Order matters: the join must exist before the projection references its alias.

### Editing a view

`_view_change` finds the alias the view uses for the fact table, builds
`<alias>.<column>` (or the bare column if the view uses no alias) and appends it
to the projection. Views are only reached here when job 3 marked them `Modify`,
so aggregate views never arrive.

### Why `sqlkit` rather than regular expressions

`sqlkit` tokenises the SQL with a scanner that understands string literals, line
and block comments, parentheses and `CASE` blocks. Depth tracking is what makes
the edits safe:

- `projection_span` finds the `FROM` that terminates a `SELECT` **at the same
  nesting depth**, so a `CASE … END` inside the projection does not hide it and
  a subquery's `FROM` is not mistaken for the outer one.
- `from_clause_span` is anchored on a specific `SELECT`, because a procedure
  that opens with `DELETE FROM target` has a `FROM` belonging to no projection
  at all.
- `split_projection` splits on top-level commas only, so a function call with
  several arguments stays one projection item.
- Both insertion helpers detect the existing indentation and reuse it, and
  preserve trailing whitespace, so the diff shows one added line.

`suggest_alias` derives a seed from the table name with the `dim_` / `fact_` /
`stg_` prefix stripped, takes the initials of the remaining words, and appends a
number if that alias is already used in the statement.

### The rollback

`_rollback` restores in reverse order of application:

1. Each edited object's original definition, verbatim from `change.before`, in
   reverse.
2. `ALTER TABLE … DROP COLUMN`, only if the column was actually added.
3. A commented call to the loader, to rebuild the snapshot with the original
   definition.

Because it is built from captured `before` text rather than regenerated, it
restores exactly the definition that was in the catalog at run time, including
formatting.

## The deployment script

`deployment_script(context)` is a module-level function, not a method, because
job 10 calls it to write `Generated_SQL.sql`. It assembles, in execution order:
the migration, each edited object's `after` definition with its summary as a
comment, then a `CALL` to the loader so the new column is populated.

## Halt conditions

| Condition | Message | What the user should do |
| --- | --- | --- |
| Missing metadata or impact | *SQL generation requires the metadata document and impact matrix.* | Out-of-order pipeline; tests only. |
| A `Modify` object is absent from the catalog | *sql_change_generation failed: Stored procedure … is missing from the catalog* | Fix the catalog; the impact matrix and the information schema disagree. |

The second case is raised as a `ValueError` and converted to a halt by
`Agent.run`, so the run report shows the status `failed` rather than `halted`.
It indicates an internally inconsistent catalog, since job 3 took the object
name from the same repository.

A `SqlEditError` from `sqlkit` — SQL whose structure the scanner cannot handle —
surfaces the same way.

## Warnings

None of its own. It copies job 3's warnings into `change_set.notes`.

## Key functions

| Function | Responsibility |
| --- | --- |
| `execute` | Decides on the migration, dispatches the edits, builds the rollback. |
| `_header` | The provenance comment block on every generated script. |
| `_migration` / `_rollback` | The forward and reverse DDL. |
| `_procedure_change` / `_view_change` | The two edit strategies. |
| `deployment_script` | Assembles the deployable script for job 10. |
| `sqlkit.add_projection_column`, `add_insert_column`, `add_join` | The three structural edits. |
| `sqlkit.alias_for_table`, `suggest_alias` | Alias discovery and allocation. |
| `sqlkit.unified_diff` | The reviewable diff. |

## Tests and extension points

Covered by `tests/test_agents_impact_sql.py` (both join strategies end to end)
and `tests/test_sqlkit.py` (the editing primitives, including the `CASE`,
subquery and `DELETE FROM` cases that motivate the scanner).

When changing this job:

- **Add a `sqlkit` test before adding a `sqlkit` feature.** The editing
  primitives are the part most likely to corrupt a hand-written procedure, and
  corruption is caught late — job 6 is what notices, and only if the SQL fails
  to parse.
- **Every edit needs a matching rollback.** The rollback is built from
  `ObjectChange.before`, so a new edit type gets reversal for free *only* if it
  goes through `ObjectChange`. Side-effecting edits outside that structure will
  not be reversed.
- **The generated SQL is Redshift-flavoured but executed in SQLite.** Dialect
  translation lives in `WarehouseSandbox.translate`, not here. If you emit a
  construct SQLite cannot run, teach `translate` about it rather than weakening
  the generated SQL.
- **Nothing here executes anything.** This job produces text. Execution is jobs
  6 and 7, which is what keeps `--no-execute` a clean switch.
