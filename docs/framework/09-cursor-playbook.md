# Cursor Playbook — Running the Framework in Cursor

This page maps every stage to the Cursor features that support it, and lists
what is checked into this repository to make that work. The goal is that a
developer can drive the whole lifecycle from the Agent chat by typing the
next slash command, with rules enforcing standards in the background.

## Cheat sheet

| I want to… | Type in Agent chat | What happens |
|-----------|--------------------|--------------|
| Turn a raw business request into an intake doc | `/intake` + paste the request | Drafts `docs/features/REQ-nnn-slug/intake.md`; marks gaps `[UNKNOWN]` / `[ASSUMED]` |
| Draft a PRD from the intake | `/prd` (with the feature folder open) | Writes `prd.md` with FR/NFR/AC IDs |
| Find and register ambiguity | `/clarify` | Applies the ambiguity checklist; writes/updates `open-questions.md`; annotates the PRD |
| Produce a technical plan | `/tech-plan` or Plan mode (Shift+Tab) | Writes `technical-plan.md` with traceability table, steps, test strategy |
| Get an independent plan review before a human | `/plan-reviewer` | Read-only subagent checks plan vs. PRD and the G2 checklist |
| Implement the next plan step | `/implement` | One step, explained then coded, with docs and `[ASSUMED]` markers |
| Write unit tests from ACs | `/unit-tests` | Tests named by AC; updates `test-plan.md` |
| Draft tests for a module in the background | `/test-writer` | Background subagent |
| Document the code / create a doc | `/document-code` | Adds docstrings and module headers; creates or refreshes `feature-doc.md`, README sections, ADRs |
| Check release readiness | `/release-check` | Fills `release-checklist.md`; lists Missing items |
| Write the PR summary from the diff | `@Branch (Diff with Main)` + "write the PR Summary of change" | Uses the actual diff |
| Review my changes like Bugbot before pushing | `/review` or `/review-bugbot` (built-in) | Local pre-push review |
| Run any of the above without opening the editor | `agent -p "/intake …"` (Cursor CLI) | Headless; see below |

## What is checked into the repo

```
AGENTS.md                      # Always-on instructions for any agent working in this repo
.cursor/
├── rules/
│   ├── workflow.mdc           # Always: stage gating, [ASSUMED] discipline, commit format, where artifacts live
│   ├── code-documentation.mdc # Auto-attached to source files: docstring / header / TODO standards
│   ├── testing.mdc            # Auto-attached to test files: naming by AC, determinism, unhappy paths
│   └── docs.mdc               # Auto-attached to docs/**: template use, IDs, no inline TBDs
├── skills/
│   ├── intake/SKILL.md        # /intake
│   ├── prd/SKILL.md           # /prd
│   ├── clarify/SKILL.md       # /clarify
│   ├── tech-plan/SKILL.md     # /tech-plan
│   ├── implement/SKILL.md     # /implement
│   ├── unit-tests/SKILL.md    # /unit-tests
│   ├── document-code/SKILL.md # /document-code
│   └── release-check/SKILL.md # /release-check
├── agents/
│   ├── plan-reviewer.md       # read-only reviewer subagent
│   ├── test-writer.md         # background test-drafting subagent
│   └── doc-writer.md          # documentation subagent
└── BUGBOT.md                  # What Bugbot should look for on every PR
.github/
├── PULL_REQUEST_TEMPLATE.md   # Stage checklist G2–G5, links, test evidence, deployment notes
├── ISSUE_TEMPLATE/business-requirement.yml   # Form business users fill in
└── workflows/pr-gates.yml     # PR hygiene checks + auto-detected unit test run
```

## Feature-by-feature

### Rules (`.cursor/rules/*.mdc`)

Rules are short standing instructions injected into the agent's context.
Four are provided:

- `workflow.mdc` (`alwaysApply: true`) — tells the agent about the stages,
  the feature-folder layout, the `[ASSUMED]` rule, the commit format, and
  that it must not skip a gate (e.g. not write code when no approved plan
  exists).
- `code-documentation.mdc` (globs on source files) — docstring and header
  requirements, `TODO` must reference `OQ-n`/issue, comments explain why.
- `testing.mdc` (globs on test files) — AC-based naming, AAA, determinism,
  unhappy paths, no assumption-encoding.
- `docs.mdc` (globs on `docs/**`) — use the templates, keep IDs stable,
  no `TBD` in approved docs.

**Adjust the `globs`** in `code-documentation.mdc` and `testing.mdc` to the
project's actual source and test paths once the stack is chosen. Rules apply
to Agent chat only — not Tab completions and not Bugbot.

### Skills (`.cursor/skills/<name>/SKILL.md`)

Skills are on-demand procedures invoked with `/name` (or auto-selected by
the agent when the description matches). Each stage skill knows its template,
its input artifacts, its gate checklist, and what to write where. They are
plain markdown; edit them as the process evolves. Because they live in the
repo, everyone gets the same behaviour, and Cloud Agents get them
automatically.

### Subagents (`.cursor/agents/*.md`)

- `plan-reviewer` is `readonly: true` — it cannot change files, only report.
  Use it before asking a human for the G2 review.
- `test-writer` is `is_background: true` — drafts tests while you keep
  working.
- `doc-writer` produces and refreshes documentation artifacts.

### Plan mode

Shift+Tab in the chat input switches to Plan mode. The agent asks clarifying
questions, researches the codebase, and produces an editable plan file. Use
*Save to workspace* and place it at
`docs/features/REQ-nnn-slug/technical-plan.md`, then reshape it to the
template (or ask `/tech-plan` to do that). Clarifying questions Plan mode
raises about *requirements* belong in `open-questions.md`.

### Bugbot (`.cursor/BUGBOT.md`)

Bugbot reviews every PR push and posts inline comments. `.cursor/BUGBOT.md`
tells it the project-specific things to look for: `[ASSUMED]` markers
without an `OQ`, bare `TODO`s, missing docstrings on public functions, tests
that assert implementation rather than AC, missing `REQ-` in the PR title,
and changed code without a test-plan update. Trigger manually with a PR
comment `bugbot run`. Make the `Cursor Bugbot` check required in branch
protection if you want it as a hard gate.

### Cloud Agents

Cloud Agents run the same skills and rules on a VM, work on a branch, and
open PRs. Useful for:

- Kicking off intake + PRD drafting from a GitHub issue: comment
  `@cursor run /intake on this issue and open a draft PR with the feature folder`.
- Long-running implementation of an approved plan while the developer does
  something else; the developer still reviews each PR.
- Auto-fixing CI failures on PRs it created (Teams plans).

Add `.cursor/environment.json` once the project has a concrete toolchain so
the Cloud Agent VM can install dependencies and run tests. Keep secrets in
the Cursor dashboard, never in the repo. The *Cursor Cloud specific
instructions* section in `AGENTS.md` is where you put anything the cloud
agent needs to know that a desktop developer would not.

### Cursor CLI (headless)

The `agent` CLI runs the same skills and rules from a terminal or CI:

```bash
curl https://cursor.com/install -fsS | bash        # once
export CURSOR_API_KEY=...                           # from Dashboard → API Keys
agent -p "/document-code refresh docs/features/REQ-042-invoice-export/feature-doc.md from the current diff" --force
```

In CI, follow the "restricted autonomy" pattern: let the agent edit files,
and have deterministic workflow steps commit, push, or comment. Add
`.cursor/cli.json` with a `deny` list (e.g. `Shell(git push)`) if you use it
in automation.

### Hooks (optional)

`.cursor/hooks.json` can run scripts on agent events. Two useful ones for
this framework, if you want them:

- `afterFileEdit` → run the project formatter so the agent's edits are
  always formatted.
- `stop` → run `scripts/check-feature-docs.sh` and return a
  `followup_message` if a changed feature folder is missing a required
  artifact.

Not enabled by default; add when the toolchain is known.

## Making it easy for developers

- **One command per stage.** Nobody has to remember the template paths or
  the gate checklist; the skill does.
- **The PR is the dashboard.** Stage labels and the checklist in the PR
  description show where any requirement is without opening docs.
- **Artifacts are next to each other.** One folder per requirement.
- **Rules do the nagging.** Documentation and test standards are applied
  while code is generated, not requested in review.
- **The framework is versioned with the code.** Change the process by
  changing the markdown in a PR, like any other change.

## Things that are deliberately *not* relied on

- `@Docs`, `@Web`, Notepads, Memories, and `.cursorrules` — deprecated or
  removed in current Cursor versions. Guidance lives in rules, skills, and
  markdown files in the repo instead.
- Command arguments (`$ARGUMENTS`) — not supported; skills operate on the
  current context (open files, chat text, the branch diff).
- `.cursor/commands/` — still works but superseded by skills; skills with
  `disable-model-invocation: true` behave identically. Everything here is a
  skill.
