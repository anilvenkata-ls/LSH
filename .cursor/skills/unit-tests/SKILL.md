---
name: unit-tests
description: Stage 6 — derive unit tests from the PRD acceptance criteria and the plan's test strategy (named by AC ID, with unhappy paths), run them, and update test-plan.md so every AC has a row. Use when the user says "write tests", "unit tests", or "test coverage for AC-n".
---

# /unit-tests — Tests from acceptance criteria

Process reference: `docs/framework/07-unit-testing.md`.
Standards: `.cursor/rules/testing.mdc` (applied automatically).
Template: `docs/templates/test-plan.md`.

## Inputs

- `prd.md` §11 (acceptance criteria) and §7 (edge cases).
- `technical-plan.md` §7 (test strategy, coverage target).
- The implementation under test (for structure, not for expected values).
- Project test conventions (runner, directory, naming) — discover from the
  repo; ask if none exist.

## Procedure

1. **List the ACs** the user asked for (default: all ACs whose plan test
   type is *unit* and that have no Passing row in `test-plan.md`).
2. **For each AC, before writing code, list the test cases:** the happy
   path from the Given/When/Then, plus unhappy paths from PRD §7 and the
   checklist (empty, boundary, invalid, downstream failure, permission
   denied, duplicate). Show this list to the user first.
3. **Write the tests.** Names carry the AC ID. AAA structure. Fakes for
   clock/network/random/filesystem. Expected values come from the AC text;
   if an expected value is not derivable from the PRD, do not invent it —
   raise an `OQ` (Assumption) and mark the test skipped with the reference.
4. **Add fixtures** with a header comment describing the scenario.
5. **Run the suite** and report pass/fail and coverage on changed files if
   the toolchain provides it.
6. **Update `test-plan.md`:** create from template if missing; fill §1 rows
   for each AC, §2 unhappy paths, §4 fixtures, header coverage figure.
7. **Fill the traceability column** in `technical-plan.md` §2 with the test
   names.
8. **Report:** ACs now covered, ACs still uncovered and why, `OQ`s raised,
   the G4 checklist status.

## Rules

- Do not weaken a test to make it pass; if the code is wrong, say so.
- Do not assert implementation details (private state, call counts) unless
  the AC is about them.
- No flaky constructs (sleeps, real time, ordering assumptions on sets).
- Keep the unit suite fast; propose `tests/integration/` for anything
  touching real I/O.
