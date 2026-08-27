# Patient Collections PBI - Visual Change Request

Live report: [Patient Collections](https://app.powerbi.com/groups/2f0dc0f6-8d38-4d3d-82fd-28e5710dfe85/reports/20c3819f-1d2d-44d0-b2a1-f19a14d9ffcf)

This folder is the landing place for the production (or Dev) PBIR export. An LLM can apply the scoped edits in `visual-changes.json` once the report definition is here and each change targets exactly one visual.

## Current blockers

1. The report is not in git. The repo had no `.pbip`, `.pbix`, or PBIR `definition/` files.
2. Service calls without credentials failed: Power BI REST `403`, Fabric `401`.
3. The ticket title is "Visual Change Request" but it does not name the labels, fields, sort, or slicer behavior to change.

## How to unblock

1. In Power BI Desktop, enable **Store reports using enhanced metadata format (PBIR)** and export this report as a Power BI Project.
2. Copy the `*.Report` folder here as `PatientCollections.Report`.
3. Replace the empty `changes` array in `visual-changes.json` with one object per requested edit. Use `PYTHONPATH=src python3 -m pbi_visual_changes inventory reports/patient-collections/PatientCollections.Report` to get page and visual names.
4. Dry-run, then apply:

```bash
PYTHONPATH=src python3 -m pbi_visual_changes apply reports/patient-collections/visual-changes.json --repo-root . --dry-run
PYTHONPATH=src python3 -m pbi_visual_changes apply reports/patient-collections/visual-changes.json --repo-root .
```

Publish the updated PBIR to a Dev workspace first. Do not overwrite production until RCM BA validation, source-data checks, refresh, and regression review from the user story are complete.
