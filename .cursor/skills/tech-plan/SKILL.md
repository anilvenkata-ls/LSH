---
name: tech-plan
description: Stage 4 — produce docs/features/REQ-nnn-slug/technical-plan.md from an approved PRD and the codebase, with FR/AC traceability, affected areas, small implementation steps, test strategy, risks, and rollout; then prepare it for developer review (G2). Use when the user says "plan this", "technical design", or "tech plan". No code is written.
---

# /tech-plan — Technical plan for developer review

Process reference: `docs/framework/05-technical-plan-and-review.md`.
Template: `docs/templates/technical-plan.md`.

## Preconditions

- `prd.md` status is `Approved` and G1 checklist is ticked. If not, stop
  and say which gate is unmet; offer `/clarify` or `/prd`.
- No Open Blocking `OQ`s. If there are, list them and stop.

## Procedure

1. **Research the codebase before designing.** Find modules the PRD
   touches or should reuse; existing patterns for similar features; data
   access layer; test conventions; config/flag mechanism. Cite files.
2. **Raise technical questions** the PRD author could not know (API limits,
   migration constraints, existing behaviour conflicts). Add them to
   `open-questions.md` with stage `plan`; mark Blocking if they change the
   approach.
3. **Write the plan** from the template:
   - §1 Approach with rejected alternatives; propose an ADR if the choice
     outlives this feature.
   - §2 Traceability: **every** FR/AC/NFR → step(s). Nothing in the plan
     that is not in the PRD.
   - §3 Affected areas with real file paths; new dependencies with why.
   - §4–5 Interfaces and data changes, each with backward compatibility and
     rollback.
   - §6 Steps: small (< ~400 changed lines), ordered, each with a "done
     when". Tests for a step belong in the same step where practical.
   - §7 Test strategy per AC + unhappy paths + coverage target.
   - §8 Documentation impact — which docs will be created/updated.
   - §9–12 Security, risks, rollout/rollback, out of scope.
4. **Self-check against the G2 checklist** at the bottom of the template
   and fix gaps.
5. **Recommend the review path:** run `/plan-reviewer` (read-only subagent),
   then commit the plan (`REQ-nnn: add technical plan`), push, and request a
   human review comment "Plan approved" on the PR.

## Do not

- Write production code or tests. Design only.
- Mark the plan `Approved`; the human reviewer does that.
- Skip the traceability table or leave an FR without a step.

## If the user used Plan mode instead

Take the saved plan file, reshape it into the template sections, keep the
agent's reasoning under §1, and run the same self-check.
