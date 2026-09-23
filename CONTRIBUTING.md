# Contributing — developer quickstart

Everything below is driven from the Cursor Agent chat. Full process:
[docs/framework/00-overview.md](docs/framework/00-overview.md). Cursor
specifics: [docs/framework/09-cursor-playbook.md](docs/framework/09-cursor-playbook.md).

## The loop, in commands

| # | Stage | You type | You get | Gate |
|---|-------|----------|---------|------|
| 1 | Intake | `/intake` + paste the request | `docs/features/REQ-nnn-slug/intake.md` + first `open-questions.md` | G0 — product owner accepts |
| 2 | PRD | `/prd` then `/clarify` | `prd.md`, `open-questions.md` with Blocking / Non-blocking items | G1 — business user signs off; no Open Blocking `OQ` |
| 3 | Branch + PR | `git checkout -b feature/REQ-nnn-slug main`, commit the folder, push, open **draft** PR | PR with stage checklist | — |
| 4 | Plan | `/tech-plan` (or Plan mode: Shift+Tab), then `/plan-reviewer` | `technical-plan.md` | G2 — another developer comments "Plan approved" |
| 5 | Code | `/implement` (one step per call) | Documented code, one commit per step | — |
| 6 | Tests | `/unit-tests` | AC-named tests, `test-plan.md` | G4 — CI green, coverage met |
| 7 | Docs | `/document-code` | Doc comments, `feature-doc.md`, ADR proposals | G3 — code review + Bugbot clean |
| 8 | Release | `/release-check` | `release-checklist.md` | G5 — release owner approves, label `stage:ready-to-deploy` |

Labels move at each gate: `stage:prd` → `stage:prd-approved` → `stage:plan`
→ `stage:implementation` → `stage:testing` → `stage:ready-to-deploy`.

## Rules you will bump into

- **No code before an approved plan.** The `workflow` rule and CI both
  enforce it. If you are asked to "just build it", run `/tech-plan` first;
  for an S-size change the plan can be half a page.
- **Never guess silently.** Write `[ASSUMED: … — OQ-n]` and add the `OQ`.
  CI rejects `[ASSUMED]` without an `OQ` reference.
- **`TODO(OQ-n)` or `TODO(#issue)`, never bare `TODO`.**
- **Tests are named after acceptance criteria** (`test_ac3_…`).
- **Commits:** `REQ-nnn: imperative summary`, one logical change each.
- **PR title** carries the `REQ-nnn`; PR body links the feature folder.
- Process-only changes (docs, CI, framework) use titles starting with
  `docs:`, `chore:`, `process:`, or `ci:` — those skip the requirement
  checks.

## Run the PR gate locally

```bash
scripts/check-pr-gates.sh --title "REQ-042: add invoice export" --body "$(gh pr view --json body -q .body)" --base origin/main
```

## Reviewing

- **Plan review (G2):** read only `technical-plan.md`. Use the checklist at
  its foot. Comment "Plan approved" or request changes. Do not wait for code.
- **Code review (G3):** confirm the diff matches the plan; check
  documentation and tests against the standards; resolve Bugbot threads.
- Author and reviewer must be different people.

## Deploying

_Project-specific: record the deployment mechanism here (pipeline, manual
release steps, windows, who runs it) and link it from
`release-checklist.md` §3._

## Changing the process

The framework is markdown in this repo. Propose changes with a normal PR
titled `process: …`. Skills live in `.cursor/skills/`, rules in
`.cursor/rules/`, templates in `docs/templates/`.
