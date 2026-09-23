# Features

One folder per requirement. Folder name: `REQ-<3+ digit id>-<short-slug>`.
IDs are allocated sequentially; `/intake` does this automatically.

Each folder holds the artifacts for its stage, always from the templates in
[`../templates/`](../templates/):

| File | Created by | Stage |
|------|-----------|-------|
| `intake.md` | `/intake` | 1 |
| `open-questions.md` | `/intake`, `/clarify` (updated by every stage) | 1+ |
| `prd.md` | `/prd` | 2 |
| `technical-plan.md` | `/tech-plan` or Plan mode | 4 |
| `test-plan.md` | `/unit-tests` | 6 |
| `feature-doc.md` | `/implement`, `/document-code` | 5–7 |
| `release-checklist.md` | `/release-check` | 8 |

## Index

| ID | Title | Stage label | PR |
|----|-------|-------------|----|
| [REQ-000](REQ-000-example-invoice-export/) | Example — invoice export (worked example, not a real requirement) | — | — |

Add a row when you create a folder; `/intake` will remind you.
