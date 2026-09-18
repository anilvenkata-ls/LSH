# Taking the platform to a real environment

The pipeline runs today against the seeded catalog and the SQLite sandbox. Everything the agents
need arrives through two boundaries: the metadata files and the sandbox. Replace those and the
agents keep working unchanged.

## 1. Populate the metadata files

`rcm-change run --metadata-dir ./metadata` reads the same file names as
`src/rcm_change_platform/catalog/seeds/`. Each one has a natural source in the RCM stack.

### `information_schema.json`

Tables, columns, relationships, view definitions and stored procedure bodies.

```sql
-- tables and columns
SELECT table_schema, table_name, column_name, data_type, is_nullable, ordinal_position
FROM information_schema.columns
WHERE table_schema IN ('rcm', 'staging');

-- view definitions
SELECT schemaname, viewname, definition FROM pg_views WHERE schemaname IN ('rcm', 'staging');

-- stored procedure bodies
SELECT n.nspname, p.proname, pg_get_functiondef(p.oid)
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'rcm';
```

Two fields have no source in the catalog and must be curated, because the quality of the impact
analysis depends on them:

- **`relationships`** — Redshift does not enforce foreign keys, so declare them (or mine them from
  the join predicates in the procedure bodies). This is what lets the platform plan a new join.
- **`routines[].reads` / `writes`** — derive by parsing each procedure body, then review. The
  impact graph is only as complete as these lists.

`business_keys` on each table drives the duplicate test, and `layer` (`staging`, `dimension`,
`fact`) tells the impact agent which table feeding a report is the one to alter.

### `data_dictionary.json`

Export from the governance tool (Collibra, Alation, Purview or the team's spreadsheet). The
`synonyms` list is what makes "fin class" resolve; `domain_values` generates the domain test;
`certified` and `pii` drive the governance checklist items.

### `etl_components.json`

From the Glue Data Catalog and job definitions, the Lambda inventory and the Step Function ASL.
Record `reads`, `writes`, `calls`, `refreshes` and `orchestrates`, which become the control edges
that flag components for review.

### `power_bi.json`

From the Power BI REST API and the dataset's TMDL/TMSL definition:
`GET /groups/{groupId}/datasets`, `.../datasources`, `.../reports` and `GET .../reports/{id}/pages`.
Tables, columns, measures, relationships and visual field bindings are all needed for the visual
impact list to be accurate. The `sources` on each dataset must use the same object names as the
information schema, since that is how the two graphs join.

### `jira_tickets.json` and `documentation.json`

From the Jira REST API (`/rest/api/3/search`) and the docs repository. Tag each entry with the
catalog object names it concerns. These only add context to the requirement document, so they can
be sparse at first.

### `sample_data.json`

Rows for the sandbox. Use de-identified or synthetic data — never production PHI. The rows need
to exercise the joins the ETL performs and the domain values the tests assert; a few dozen rows
per dimension is enough.

## 2. Decide how the change is validated

The sandbox proves the SQL parses, the column populates and the totals reconcile, against sample
data in SQLite. It does not prove behaviour against production volumes or Redshift-specific SQL.
For a full environment, run the same suite where the data is:

- point `WarehouseSandbox` at a Redshift connection (the class isolates `translate`, `query` and
  `execute_script`, which is where the dialect handling lives), or
- keep the sandbox as the fast pre-check and execute `Unit_Tests.sql` and `Integration_Tests.sql`
  in the dev environment as the authoritative gate.

Either way, the reconciliation contract is the same: the before snapshot must be taken *before*
the migration runs.

## 3. Wire it into the change process

A reasonable sequence for a pilot:

1. Analyst runs `rcm-change run "<ticket summary>" --request-id RCM-1610 -o ./artifacts`.
2. CI treats the exit code as the gate: `0` proceed, `1` blocked, `2` needs clarification.
3. A job commits `artifacts/Change_Request/` to a branch, applies `Generated_SQL.sql` to dev, runs
   the two test scripts there, and opens a pull request with `PR_Description.md` as the body.
4. A data engineer reviews the diffs and the validation report; the Power BI change is applied by
   a human following `PowerBI_Change_Plan.md`.
5. Deployment applies the same script to production; `Rollback_Script.sql` is the documented
   reversal.

Keep the human approval step. The platform is designed to make the analysis and the evidence
cheap, not to remove the reviewer.

## 4. What to extend first

In rough order of value:

- **Column-level lineage.** The graph is object-level today. Column-level edges would let the
  impact agent tell a view that selects the changed column from one that does not.
- **Power BI write-back.** `PowerBIPlan` already carries the TMDL snippet; applying it through the
  XMLA endpoint or a TMDL commit turns a manual step into a reviewable diff.
- **More change types.** `ChangeType` only automates `add_column`. Renames, datatype changes and
  measure additions each need their own generation and test strategy, and each should halt rather
  than guess until implemented.
- **Warehouse-native execution.** Running the generated suite in Redshift removes the dialect gap
  between the sandbox and production.

## Operational notes

- **Secrets.** The LLM keys are read from the environment (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`).
  Nothing else in the platform makes a network call; with no key configured it is fully offline.
- **Determinism.** Without an LLM the pipeline is deterministic, so artifacts diff cleanly between
  runs and are safe to commit.
- **Runtime.** A full run against the seeded catalog, including sandbox execution, takes well
  under a second, which is what makes it usable as a CI gate.
