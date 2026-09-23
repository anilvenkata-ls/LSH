# Stage 2 — Product Requirements Document (PRD)

**Input:** approved `intake.md`.
**Output:** `prd.md` and `open-questions.md` in the feature folder; PRD status
`Approved`.
**Owner:** Product owner / BA writes; business user signs off.
**Cursor:** `/prd` drafts the PRD from the intake; `/clarify` runs the
ambiguity pass and maintains `open-questions.md`.

## Purpose

Translate the business problem into an unambiguous, testable specification
that a developer can plan against **without going back to the business user
for the basics**. The PRD is the contract between business and engineering.

## Steps

1. **Draft.** Run `/prd` in Cursor with `intake.md` open. The skill produces
   `prd.md` from `docs/templates/prd.md`. Every requirement gets an ID
   (`FR-1`, `FR-2`, … for functional; `NFR-1`, … for non-functional) and every
   acceptance criterion an ID (`AC-1`, …). These IDs are referenced later in
   the plan, the tests, and the PR.
2. **Ambiguity pass.** Run `/clarify`. It reads the PRD, applies the checklist
   in [03-ambiguity-handling.md](03-ambiguity-handling.md), and writes each
   finding to `open-questions.md` with a severity. It also rewrites vague
   sentences in the PRD and marks them `[ASSUMED: …]` so the author sees what
   was interpreted.
3. **Resolve questions with the business user.** Take *only* `open-questions.md`
   to the requester — not the whole PRD. Record each answer in the register
   and fold it back into the PRD. Repeat `/clarify` until no **Blocking**
   items remain.
4. **Review acceptance criteria for testability.** Each AC must be written so
   that a unit or integration test could pass or fail it. Prefer the
   Given/When/Then form. "The export should be fast" is not an AC;
   "Export of 10,000 rows completes in under 5 s on the staging dataset" is.
5. **Sign-off.** The business user approves by name and date in the PRD
   header. Product owner sets status `Approved`, moves the issue label to
   `stage:prd-approved`. Gate G1 passed.

## Content rules

- **Goals and Non-goals are both mandatory.** Non-goals are where scope creep
  is prevented. If you cannot think of a non-goal, you have not thought about
  the boundary.
- **One requirement per line, each with an ID.** No "and/or" inside a
  requirement — split it.
- **Every FR has at least one AC.** Every AC references one or more FRs.
- **NFRs are numeric where possible** — latency, volume, availability,
  retention, accessibility level, supported browsers/locales.
- **Data requirements** list every field the feature reads or writes, its
  source of truth, and any PII/compliance classification.
- **Out-of-band behaviour** — what happens on failure, on empty input, on
  concurrent use, on permissions denied. These are where most "we didn't
  think of that" bugs hide.
- **Open questions live in `open-questions.md`, not inline.** The PRD may
  reference `OQ-3` but must not contain an unresolved "TBD" once approved.

## PRD change control after approval

Once approved, changes to the PRD go through the same path: add an
`open-questions.md` entry (type *Change request*), get the business user's
answer, bump the PRD version, and note the change in the *Change log* table.
If a change invalidates the technical plan, G2 must be re-passed.
