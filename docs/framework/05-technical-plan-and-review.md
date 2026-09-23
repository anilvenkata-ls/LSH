# Stage 4 — Technical Plan and Developer Review

**Input:** approved PRD; draft PR open.
**Output:** `technical-plan.md` reviewed and approved by a second developer
(G2). Only then does code generation begin.
**Owner:** Developer (author) writes; developer (reviewer) approves.
**Cursor:** Plan mode (Shift+Tab in the chat input) or `/tech-plan`; the
`plan-reviewer` subagent for an independent first-pass review.

## Why plan first

Cursor can generate a lot of code quickly. Without an agreed plan, it will
generate a lot of *plausible* code quickly, and the reviewer sees the design
for the first time in a 40-file diff. The plan review moves design
disagreement to the point where changing direction costs minutes.

## Steps

1. **Read the PRD with the codebase open.** Note any question the PRD author
   could not have known (API limits, existing modules to reuse, migration
   constraints). Add these to `open-questions.md` with stage `plan`.
2. **Generate the plan.** Either:
   - Enter Plan mode, prompt with `@docs/features/REQ-042-…/prd.md` and
     "Produce a technical plan following docs/templates/technical-plan.md",
     answer its clarifying questions, then *Save to workspace* as
     `technical-plan.md` in the feature folder; or
   - Run `/tech-plan`, which does the same via the skill.
3. **Edit the plan yourself.** The agent's plan is a draft. Check that every
   FR and AC in the PRD is covered by at least one step, and that the *Test
   strategy* section says which ACs become unit tests, which need
   integration tests, and which are verified manually.
4. **Run the `plan-reviewer` subagent** (`/plan-reviewer` or just ask "review
   this plan"). It is read-only and checks the plan against the PRD and the
   checklist below. Fix what it finds before asking a human.
5. **Request human review.** Commit the plan, push, and request a PR review
   from a second developer. They review *only the plan file* at this point
   and comment "Plan approved" (or request changes).
6. **Pass G2.** Tick the G2 box in the PR, move label to
   `stage:implementation`.

## What the plan must contain

Template: `docs/templates/technical-plan.md`.

- **Traceability table:** FR / AC → plan step(s) → test(s). Anything in the
  PRD with no row is a gap.
- **Affected areas:** modules, services, DB tables, config, third-party APIs.
  Name files where you can.
- **Interfaces:** new/changed API endpoints, events, CLI flags, UI routes,
  with request/response shapes.
- **Data changes:** migrations, backfills, retention, and their rollback.
- **Step-by-step implementation order:** small, independently reviewable
  steps; each becomes one or more commits. Say what is done when each step
  is complete.
- **Test strategy:** for each AC — unit / integration / manual; fixtures and
  test data needed; coverage target for changed code.
- **Documentation impact:** which docs will be created or updated (feature
  doc, README, ADR, API reference).
- **Risks and mitigations:** performance, security, data loss, third-party
  dependency, rollout.
- **Rollout:** feature flag? migration order? backward compatibility?
- **Estimate** (S/M/L/XL, revised from intake) and **out-of-scope** list.

## Plan review checklist (for the reviewer and the `plan-reviewer` subagent)

- [ ] Every FR and AC in the PRD appears in the traceability table.
- [ ] No step depends on an Open Blocking `OQ`.
- [ ] Reuses existing modules where they exist; no parallel implementation
      of something already in the codebase.
- [ ] Data changes have a rollback.
- [ ] Interfaces are backward compatible, or the break is called out and
      approved.
- [ ] Security: authz checks named; no secrets in code; input validation
      stated.
- [ ] Test strategy covers failure paths, not just the happy path.
- [ ] Steps are small enough to review individually (rule of thumb:
      < 400 changed lines each).
- [ ] Documentation impact is listed.
- [ ] Nothing in the plan is *not* in the PRD (gold-plating).

## Re-planning

If implementation reveals the plan was wrong, update `technical-plan.md`,
note the change in its *Change log*, and ask the reviewer for a quick
re-approval of the changed section. Do not let the plan and the code drift;
the plan is later linked from the feature doc as the design record.
