# Documentation index

| Folder | Contents |
|--------|----------|
| [framework/](framework/) | The development lifecycle: one file per stage plus ambiguity handling, the Cursor playbook, and the documentation guide. Start with [00-overview.md](framework/00-overview.md). |
| [templates/](templates/) | Templates for every artifact. Skills copy from here; humans should too. |
| [features/](features/) | One folder per requirement: `REQ-nnn-slug/` with intake, open questions, PRD, technical plan, test plan, feature doc, release checklist. |
| [adr/](adr/) | Architecture decision records, `NNNN-title.md`. |

## Framework files

| File | Stage | Gate |
|------|-------|------|
| [00-overview.md](framework/00-overview.md) | All | — |
| [01-requirements-intake.md](framework/01-requirements-intake.md) | 1 Intake | G0 |
| [02-prd.md](framework/02-prd.md) | 2 PRD | G1 |
| [03-ambiguity-handling.md](framework/03-ambiguity-handling.md) | All (register, severity, checklist) | G1, G2 |
| [04-git-and-pr-workflow.md](framework/04-git-and-pr-workflow.md) | 3 Branch and PR | — |
| [05-technical-plan-and-review.md](framework/05-technical-plan-and-review.md) | 4 Plan | G2 |
| [06-implementation.md](framework/06-implementation.md) | 5 Code | G3 |
| [07-unit-testing.md](framework/07-unit-testing.md) | 6 Tests | G4 |
| [08-release-readiness.md](framework/08-release-readiness.md) | 8 Release | G5 |
| [09-cursor-playbook.md](framework/09-cursor-playbook.md) | How Cursor runs each stage | — |
| [10-documentation.md](framework/10-documentation.md) | 7 Docs — catalogue, when to create, standards | G3, G5 |
