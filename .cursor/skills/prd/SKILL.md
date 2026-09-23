---
name: prd
description: Stage 2 — draft or update docs/features/REQ-nnn-slug/prd.md from an accepted intake.md using the PRD template, with FR/NFR/AC IDs, goals and non-goals, edge cases, and data requirements. Use when the user says "PRD", "write the requirements doc", or after intake is accepted.
---

# /prd — Product Requirements Document

Process reference: `docs/framework/02-prd.md`.
Template: `docs/templates/prd.md`.
Ambiguity checklist: `docs/framework/03-ambiguity-handling.md`.

## Inputs

- `intake.md` in the feature folder (must have G0 ticked; if not, say so and
  offer `/intake`).
- `open-questions.md` if present — carry Accepted answers into the PRD.
- Existing codebase, for glossary terms and existing behaviour the PRD
  changes.

## Procedure

1. **Locate the feature folder** from the open file, branch, or ask.
2. **Create `prd.md`** from the template if missing; otherwise update in
   place and bump the version.
3. **Fill sections in this order** (each builds on the previous):
   1. Summary and Goals from *Business value* / *Desired outcome*.
   2. Non-goals — at least three; derive from what the intake did *not* ask
      for and from adjacent features a reader might assume.
   3. Users and roles; user stories.
   4. Functional requirements — one per row, `FR-n`, must/must not/may, no
      and/or, priority.
   5. Behaviour details and edge cases — for every FR walk section C of the
      ambiguity checklist (empty/max, duplicates, concurrency, permissions,
      downstream failure, cancel, time zones).
   6. Data requirements — every field read/written, source of truth,
      validation, classification, retention.
   7. NFRs — numeric; if the intake gives no number, write `[ASSUMED: …]`
      with a sensible default and raise an `OQ`.
   8. Interfaces and integrations.
   9. Acceptance criteria — Given/When/Then, `AC-n`, each referencing FRs,
      each with a verification type. Every FR must have at least one AC.
   10. Rollout / success measurement, glossary, assumptions table (§14),
       change log.
4. **Mark every interpretation** `[ASSUMED: …]` inline and list it in §14
   with an `OQ` reference. Add the `OQ` entries to `open-questions.md`.
5. **Run the G1 checklist** at the bottom of the PRD and report which items
   are unmet. Recommend running `/clarify` next.

## Quality bar

- A developer should be able to plan from this PRD without talking to the
  business user about anything except the items in `open-questions.md`.
- No vague quantifiers, no *should*, no `TBD`.
- ACs are falsifiable: someone could write a test that fails.

## Do not

- Set status `Approved` — only the product owner does that after business
  sign-off.
- Add requirements the intake does not support (gold-plating). If you think
  something is missing, raise it as an `OQ` (type Question).
