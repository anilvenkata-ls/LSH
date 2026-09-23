# Development Lifecycle Framework — Overview

This framework takes a piece of work from a business user's request to a
deployable, tested, documented change. It is built to be run inside Cursor,
with each stage backed by a slash command (`/intake`, `/prd`, `/clarify`,
`/tech-plan`, `/implement`, `/unit-tests`, `/document-code`, `/release-check`)
so developers do not have to remember the process — they type the next command.

## The pipeline

```
 Business user            Product / BA              Developer                  Developer + CI                Release owner
┌──────────────┐   ┌───────────────────┐   ┌────────────────────┐   ┌───────────────────────────┐   ┌────────────────────┐
│ 1. Intake    │──▶│ 2. PRD            │──▶│ 3. Git branch + PR │──▶│ 4. Tech plan (reviewed)   │──▶│                    │
│ raw request  │   │ + ambiguity pass  │   │ draft PR opened    │   │ 5. Implement (suggested   │   │ 8. Release         │
│              │   │ (/clarify)        │   │                    │   │    code after review)     │   │    readiness       │
│              │   │                   │   │                    │   │ 6. Unit tests             │   │    → deploy        │
│              │   │                   │   │                    │   │ 7. Code documentation     │   │                    │
└──────────────┘   └───────────────────┘   └────────────────────┘   └───────────────────────────┘   └────────────────────┘
      G0                    G1                      G2                     G3          G4                    G5
```

Every arrow is a **gate**. A gate is a short checklist owned by a named role.
Nothing moves forward until the gate is ticked; this is what keeps ambiguity
from leaking downstream into code.

| Gate | Name | Owner | Passes when |
|------|------|-------|-------------|
| G0 | Intake accepted | Product owner / BA | `intake.md` complete, requester identified, business value stated |
| G1 | PRD approved | Business user (sign-off) + Product owner | No **blocking** open questions; all assumptions acknowledged; acceptance criteria testable |
| G2 | Plan approved | Developer (reviewer ≠ author) | `technical-plan.md` reviewed; risks and test strategy agreed; PR is open as draft |
| G3 | Code complete | Developer + PR reviewer + Bugbot | Implementation matches plan; PR review comments resolved; code documented |
| G4 | Tests green | CI | Unit tests pass; coverage on changed code ≥ threshold; test plan covers every acceptance criterion |
| G5 | Ready to deploy | Release owner | `release-checklist.md` complete; PR approved; labelled `stage:ready-to-deploy` |

## Stages in one paragraph each

1. **Requirements intake** — The business user describes what they need in
   their own words. Product/BA captures it in `intake.md` using the template.
   No solutioning yet. See [01-requirements-intake.md](01-requirements-intake.md).
2. **PRD** — The intake is expanded into a PRD with goals, non-goals, user
   stories, acceptance criteria, and non-functional requirements. An explicit
   **ambiguity pass** (`/clarify`) produces `open-questions.md`. The PRD is
   not approved while blocking questions remain. See [02-prd.md](02-prd.md)
   and [03-ambiguity-handling.md](03-ambiguity-handling.md).
3. **Git and PR** — One feature branch per requirement (`feature/REQ-042-slug`),
   one draft PR opened as soon as the PRD is approved. The PR is the single
   place where the stage, checklist, and artifacts are visible. See
   [04-git-and-pr-workflow.md](04-git-and-pr-workflow.md).
4. **Technical plan and developer review** — The developer (with Cursor's Plan
   mode or `/tech-plan`) writes `technical-plan.md`: affected modules, data
   changes, interfaces, test strategy, risks. A second developer reviews it.
   **Code is only generated after this review.** See
   [05-technical-plan-and-review.md](05-technical-plan-and-review.md).
5. **Implementation** — `/implement` generates code step by step from the
   approved plan; the developer reviews each step. Documentation is written
   alongside the code, not after. See [06-implementation.md](06-implementation.md).
6. **Unit tests** — `/unit-tests` derives tests from the acceptance criteria
   and the plan's test strategy; each acceptance criterion maps to at least
   one test. See [07-unit-testing.md](07-unit-testing.md).
7. **Documentation** — Code-level docs (docstrings, module README), the
   feature document (`feature-doc.md`), and any ADRs. Generated on demand
   with `/document-code`. See [10-documentation.md](10-documentation.md).
8. **Release readiness** — `/release-check` fills `release-checklist.md`;
   the release owner confirms rollout, rollback, monitoring, and comms.
   See [08-release-readiness.md](08-release-readiness.md).

## Roles

| Role | Responsibilities | Typical person |
|------|------------------|----------------|
| Business user (requester) | Describes the need, answers clarifying questions, signs off the PRD, accepts the delivered feature | Ops lead, finance manager, sales, etc. |
| Product owner / BA | Runs intake, writes the PRD, owns `open-questions.md`, decides priority | PM, BA, or tech lead in small teams |
| Developer (author) | Writes the technical plan, implements, tests, documents | Engineer assigned to the feature |
| Developer (reviewer) | Reviews plan at G2 and code at G3; must not be the author | Any other engineer |
| Release owner | Confirms G5, coordinates deploy | Tech lead / on-call / DevOps |

In a small team one person may hold several roles, but **author and reviewer
must be different people** at G2 and G3.

## Artifacts — one folder per feature

Everything for a requirement lives in `docs/features/<ID>-<slug>/`:

```
docs/features/REQ-042-invoice-export/
├── intake.md              # Stage 1 — business request (template: docs/templates/requirement-intake.md)
├── open-questions.md      # Stage 2 — ambiguity register (template: docs/templates/open-questions.md)
├── prd.md                 # Stage 2 — approved PRD (template: docs/templates/prd.md)
├── technical-plan.md      # Stage 4 — reviewed plan (template: docs/templates/technical-plan.md)
├── test-plan.md           # Stage 6 — AC → test mapping (template: docs/templates/test-plan.md)
├── feature-doc.md         # Stage 7 — how it works, how to run, decisions (template: docs/templates/feature-doc.md)
└── release-checklist.md   # Stage 8 — deploy readiness (template: docs/templates/release-checklist.md)
```

IDs are `REQ-<3+ digits>`, allocated sequentially. The slug is short,
lowercase, hyphenated. The same ID is used in the branch name, PR title, and
commit messages so everything is greppable.

Architecture-level decisions that outlive one feature go in `docs/adr/`.

## How Cursor fits

Each stage has a skill in `.cursor/skills/` that knows the template, the
gate, and what to ask. Rules in `.cursor/rules/` enforce documentation and
testing standards while the agent writes code. Subagents in `.cursor/agents/`
provide an independent plan reviewer, test writer, and doc writer. Bugbot
reviews every PR using `.cursor/BUGBOT.md`. The full mapping is in
[09-cursor-playbook.md](09-cursor-playbook.md).

## Where to start

- Developer new to the repo: read [CONTRIBUTING.md](../../CONTRIBUTING.md) (5 minutes), then run `/intake` on your first request.
- Business user: fill in the "Business requirement" GitHub issue form, or send the request to your product owner.
- Product owner: [01-requirements-intake.md](01-requirements-intake.md) and [03-ambiguity-handling.md](03-ambiguity-handling.md).
