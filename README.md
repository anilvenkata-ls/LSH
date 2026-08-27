# LSH Power BI report enhancements

**Yes — an LLM can apply the scoped Power BI enhancements in this user story**, but only when the report exists as PBIR text in git (or can be exported through the Fabric API). It cannot click through Power BI Desktop or the live Power BI Service UI, and it cannot safely patch production from a report URL alone.

This repository now has that as-code path. The live [Patient Collections](https://app.powerbi.com/groups/2f0dc0f6-8d38-4d3d-82fd-28e5710dfe85/reports/20c3819f-1d2d-44d0-b2a1-f19a14d9ffcf) report is **not updated yet**: there is no PBIP in git, the service rejected unauthenticated API calls, and the ticket does not list the visual edits.

## What an LLM can change

In scope for this user story, when a `*.Report/definition` folder is present:

- Visual and UI edits: titles, labels, font size, sort, slicer tab order, hide/show
- Small field-mapping or DAX edits in TMDL, if the semantic model is also exported
- Reviewable diffs so pre/post output can be compared before publish

Out of scope without extra access:

- Opening `app.powerbi.com` and dragging visuals
- Publishing to the production workspace
- Confirming refresh success or RCM BA sign-off

## Commands

Inventory a PBIR report:

```bash
PYTHONPATH=src python3 -m pbi_visual_changes inventory reports/fixtures/sample-collections.Report
```

Apply a change spec (dry-run first):

```bash
PYTHONPATH=src python3 -m pbi_visual_changes apply reports/fixtures/sample-collections.visual-changes.json --repo-root . --dry-run
PYTHONPATH=src python3 -m pbi_visual_changes apply reports/fixtures/sample-collections.visual-changes.json --repo-root .
```

Tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Patient Collections ticket

See `reports/patient-collections/` for workspace/report IDs, blockers, and the empty change spec to fill in after the PBIR export is added.
