# Stage 3 — Git and Pull Request Workflow

**Input:** approved PRD (G1 passed).
**Output:** feature branch pushed; draft PR open with the template filled in;
issue and PR labelled with the current stage.
**Owner:** Developer (author).

## Branching model

```
main ──●────────●────────────●──────▶   protected; always deployable
        \                  /
         ●──●──●──●──●──●─●            feature/REQ-042-invoice-export
```

- `main` is protected: PR required, at least one approving review, CI green,
  `Cursor Bugbot` check passing (or neutral), no direct pushes.
- **One requirement → one branch → one PR.** Branch name:
  `feature/REQ-<id>-<slug>` (or `fix/REQ-…`, `chore/REQ-…`). Cursor Cloud
  Agents create `cursor/…` branches; rename or keep, but the PR title must
  still carry the `REQ-` ID.
- Branch from the latest `main`. Rebase or merge `main` into the branch before
  requesting review; squash-merge into `main` so each requirement is one
  commit on the trunk.
- Branch lifetime should be short. If an `L`/`XL` requirement cannot merge
  within a sprint, split it into `REQ-042a`, `REQ-042b` with a parent PRD.

## Commit messages

```
REQ-042: add invoice export service

Implements FR-1, FR-2. Covers AC-1..AC-4.
Refs OQ-3 (accepted assumption: CSV only in phase 1).
```

First line: `REQ-<id>: <imperative summary>` ≤ 72 chars. Body references the
FR/AC/OQ IDs touched. This is what makes the PRD → code trail searchable.

## The pull request

Open the PR **as a draft immediately after G1**, before any code exists. The
PR then becomes the dashboard for the requirement:

1. `git checkout -b feature/REQ-042-invoice-export main`
2. Commit `docs/features/REQ-042-invoice-export/` (intake, PRD, register).
3. Push, open draft PR. `.github/PULL_REQUEST_TEMPLATE.md` pre-fills the
   stage checklist and links.
4. Add labels `REQ-042` (or the issue link) and `stage:plan`.

The PR description must contain:

- Link to the feature folder (`docs/features/REQ-042-…/`) — the `pr-gates`
  CI job checks this.
- The stage checklist (G2–G5) from the template.
- *Summary of change* — filled in at implementation time.
- *Test evidence* — how to run the tests, coverage number, screenshots if UI.
- *Deployment notes* — flags, migrations, config, rollback.

## Stage labels

| Label | Meaning |
|-------|---------|
| `stage:intake` | Issue only; intake in progress |
| `stage:prd` | PRD being drafted / questions open |
| `stage:prd-approved` | G1 passed; PR may be opened |
| `stage:plan` | Technical plan under review |
| `stage:implementation` | G2 passed; code being written |
| `stage:testing` | Code complete; tests and docs being finished |
| `stage:ready-to-deploy` | G5 passed |
| `blocked` | An Open Blocking `OQ` exists; add a comment with the ID |

Moving the label is the author's job at each gate. Labels are cheap process
state that everyone (including the business user) can read without opening
the code.

## Review flow inside the PR

| Gate | Reviewer | Reviews | How |
|------|----------|---------|-----|
| G2 | Second developer | `technical-plan.md` | PR review comment on the plan file; approve the *plan* explicitly ("Plan approved") |
| G3 | Second developer + Bugbot | Code, tests, docs | Normal PR review; Bugbot comments must be resolved or answered |
| G5 | Release owner | `release-checklist.md`, deployment notes | Final approval; mark PR ready for review → approve |

Requesting a plan review before code exists feels unusual at first. It is the
step that makes "code is suggested after developer review" real: the
reviewer agrees on the shape of the change while it costs nothing to alter.

## Working with Cursor and git

- Ask the agent to commit in logical units (`docs`, `plan`, `implementation
  step n`, `tests`, `docs update`) rather than one giant commit. The
  `workflow` rule reminds it of the commit message format.
- Cloud Agents can be told to open the draft PR (`@cursor` from the GitHub
  issue, or from cursor.com/agents). They push a branch and create the PR
  with the template.
- Use `@Branch (Diff with Main)` in chat to ask the agent to write the PR
  *Summary of change* section from the actual diff.
- Bugbot runs automatically on every push; re-trigger with a PR comment
  `bugbot run` if needed.

## Merging and after

- Squash-merge; the squash commit message is the PR title + the stage
  checklist summary.
- Delete the branch.
- Move the issue to `stage:ready-to-deploy` → closed once deployed.
- If a hotfix is needed later, it is a new `fix/REQ-nnn-…` with its own
  (light) PRD.
