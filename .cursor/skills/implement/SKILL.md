---
name: implement
description: Stage 5 — implement the next (or a named) step of an approved technical-plan.md, explaining the approach first, writing documented code with [ASSUMED] markers for any gap, running existing tests, and ticking the step. Use when the user says "implement", "build step N", or "continue the plan". Refuses if the plan is not approved.
---

# /implement — One plan step at a time

Process reference: `docs/framework/06-implementation.md`.
Standards: `.cursor/rules/code-documentation.mdc` (applied automatically).

## Preconditions

- `technical-plan.md` status is `Approved` (G2). If not: stop, name the
  gate, offer `/tech-plan`.
- The step to implement has no dependency on an Open Blocking `OQ`.

## Procedure

1. **Pick the step.** The one the user names, else the first unticked step
   in `technical-plan.md` §6. State it: "Implementing Step 3 — …".
2. **Explain first, briefly.** In a few sentences: files to touch, the
   approach, anything the plan left open. If something is open, write the
   `[ASSUMED: …]` marker, add the `OQ`, and ask for confirmation before
   continuing if it affects behaviour.
3. **Implement only this step.** Follow the plan's module boundaries and
   interfaces. Reuse existing code the plan pointed at.
4. **Document as you go** (module header with `REQ-`, public doc comments,
   why-comments, `TODO(OQ-n)` only). Document new config keys in
   `feature-doc.md` §5; create `feature-doc.md` from the template if it does
   not exist yet.
5. **Tests for this step** if the plan's test strategy assigns any here; at
   minimum run the existing suite and report the result.
6. **Tick the step** in `technical-plan.md` §6.
7. **Propose the commit:** `REQ-<id>: step N — <summary>` with FR/AC/OQ refs
   in the body. Commit if the user has asked you to manage git.
8. **Report:** what changed (files), assumptions raised, tests run, and the
   next unticked step.

## Rules

- Never go beyond the requested step, even if the next one is small.
- If implementation shows the plan is wrong, stop and propose a plan change
  (update §6 + change log) rather than diverging silently.
- No new dependency unless it is in the plan §3.
- No secrets, no environment-specific values.
- Keep the diff reviewable; mention unrelated issues, do not fix them.
