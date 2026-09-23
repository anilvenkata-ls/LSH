# LSH

This repository uses a gated, Cursor-driven development lifecycle:

```
Business request ─▶ Intake ─▶ PRD (+ ambiguity pass) ─▶ Branch + draft PR ─▶ Technical plan (developer-reviewed)
                ─▶ Implementation ─▶ Unit tests ─▶ Documentation ─▶ Release readiness ─▶ Deploy
       G0            G1                    G2                          G3         G4         G5
```

Each stage has a slash command in Cursor, a template, and a gate checklist.

| Start here | |
|------------|--|
| I'm a **developer** | [CONTRIBUTING.md](CONTRIBUTING.md) — five-minute quickstart, then [docs/framework/09-cursor-playbook.md](docs/framework/09-cursor-playbook.md) |
| I'm a **business user** | Open a [Business requirement](../../issues/new?template=business-requirement.yml) issue |
| I'm a **product owner / BA** | [docs/framework/01-requirements-intake.md](docs/framework/01-requirements-intake.md), [02-prd.md](docs/framework/02-prd.md), [03-ambiguity-handling.md](docs/framework/03-ambiguity-handling.md) |
| I want the **whole picture** | [docs/framework/00-overview.md](docs/framework/00-overview.md) |

## Layout

```
docs/framework/     process — one file per stage, plus ambiguity handling, Cursor playbook, documentation guide
docs/templates/     templates for every artifact
docs/features/      one folder per requirement (REQ-nnn-slug/) holding all its artifacts
docs/adr/           architecture decision records
.cursor/            rules, skills (/intake … /release-check), subagents, Bugbot config
.github/            PR template, business-requirement issue form, PR gate workflow
scripts/            check-pr-gates.sh (runs in CI and locally)
```
