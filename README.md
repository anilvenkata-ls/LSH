# LSH

## pbi-schema-remap

Repoints every source table of a Power BI semantic model at a Redshift schema
(default `athena_integration`) while keeping the table names. The input is never
modified; a remapped copy is written next to it (`<input>_redshift`).

### Supported inputs

| Input | Notes |
| --- | --- |
| `.pbip` or PBIP folder | Rewrites `*.tmdl` / `model.bim` under `*.SemanticModel`; the whole project is copied |
| `.pbit` | Rewrites the `DataModelSchema` entry; other entries are copied byte for byte |
| `model.bim`, `*.tmdl` | Single file |
| `.pbix` | Not editable (binary model). Save as `.pbip` or export a `.pbit` in Power BI Desktop first |

### What gets rewritten

- SQL Server navigation: `Source{[Schema="dbo",Item="Claims"]}` becomes `Schema="athena_integration"`.
- Redshift/PostgreSQL navigation: the schema step `Source{[Name="public"]}[Data]` becomes
  `Name="athena_integration"`; the table step is untouched.
- Native SQL (`Value.NativeQuery`, `Query=` options, legacy `query` partitions): `FROM`/`JOIN`
  references like `dbo.Claims`, `[RCM].[dbo].[Claims]` or `rcm."Payer Map"` become
  `athena_integration.<table>`.

With `--redshift-server` and `--redshift-database`, `Sql.Database(...)` sources are also switched
to `AmazonRedshift.Database(...)` and their navigation is converted to Redshift's
`{[Name="athena_integration"]}[Data]{[Name="<table>"]}[Data]` form. Add `--lowercase-tables` when
the Redshift table names are lowercase, because M navigation keys are case-sensitive.

### Usage

```bash
pip install -e '.[test]'

pbi-schema-remap MyReport.pbip --dry-run          # preview every change
pbi-schema-remap MyReport.pbip                    # writes MyReport_redshift/
pbi-schema-remap MyReport.pbit --only-schema dbo  # leave other schemas alone
pbi-schema-remap MyReport.pbit \
  --redshift-server my-cluster.xxxx.us-east-1.redshift.amazonaws.com:5439 \
  --redshift-database rcm --lowercase-tables

pytest
```

Redshift folds unquoted identifiers to lowercase, so a schema created as `Athena_integration`
is named `athena_integration`; pass `--schema` if yours differs. After opening the output in
Power BI Desktop, update the data source credentials and refresh.
