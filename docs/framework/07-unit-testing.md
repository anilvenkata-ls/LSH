# Stage 6 — Unit Testing

**Input:** implemented code; PRD acceptance criteria; plan test strategy.
**Output:** unit tests committed; `test-plan.md` mapping every AC to tests;
CI green with coverage at or above the threshold (G4).
**Owner:** Developer (author); CI enforces.
**Cursor:** `/unit-tests` derives tests from ACs and the plan; the
`test-writer` subagent can run in the background to draft tests for a module.

## Purpose

Tests here have two jobs: prove the acceptance criteria and protect the code
from future change. The AC mapping is what makes the first job checkable —
a test suite with 90% coverage that never exercises AC-3 has not tested the
requirement.

## Steps

1. **Start from the ACs, not the code.** Run `/unit-tests`. The skill reads
   `prd.md` (ACs) and `technical-plan.md` (test strategy), and for each AC
   marked *unit* proposes one or more test cases named after the AC:
   `test_ac3_export_rejects_more_than_10000_rows`.
2. **Add the "unhappy" cases.** For every function under test: empty input,
   boundary values, invalid input, downstream failure, permission denied.
   The ambiguity checklist section C is a good prompt list.
3. **Fill `test-plan.md`.** Template `docs/templates/test-plan.md`. One row
   per AC: test type, test name(s), status. ACs verified by integration or
   manual tests are listed too, with how and by whom.
4. **Run locally, then push.** CI runs the suite and reports coverage. The
   `unit-tests` job in `.github/workflows/pr-gates.yml` auto-detects the
   stack; adjust it once the project has a concrete toolchain.
5. **Pass G4.** Tests green; coverage on *changed files* ≥ threshold
   (default 80%; set in the plan if different); every AC has a row in
   `test-plan.md` with status *Passing* or *Verified*.

## Standards

- **Naming:** `test_<ac-id>_<behaviour>` or `it("AC-3: rejects more than
  10,000 rows")`. The AC ID must appear in the test name or a comment so
  grep proves coverage of the requirement.
- **Arrange / Act / Assert** structure, one behaviour per test.
- **Deterministic.** No real clock, network, randomness, or filesystem
  without a fake. Flaky tests are deleted or fixed, never retried into
  passing.
- **Fast.** Unit suite target: under 60 s locally. Slow tests move to an
  integration suite with its own CI job.
- **Fixtures are documented.** Test data files carry a short header
  explaining what scenario they represent.
- **Tests do not encode unacknowledged assumptions.** If you find yourself
  writing an expected value you are not sure about, that is an `OQ`, not a
  test.
- **Failure paths are tested.** At least one test per external dependency
  that simulates it failing.

## Test types and where they live

| Type | Verifies | Location | Runs in |
|------|----------|----------|---------|
| Unit | One function/class in isolation; AC logic | `tests/unit/` (or the language convention next to source) | Every push |
| Integration | Module boundaries, DB, external APIs via test doubles or sandboxes | `tests/integration/` | Every PR |
| Contract | API shapes against consumers | `tests/contract/` | Every PR |
| Manual / UAT | ACs that cannot be automated; business acceptance | Recorded in `test-plan.md` | Before G5 |

## Using Cursor well at this stage

- `/unit-tests` will propose tests; **read the assertions**. An agent can
  produce tests that pass because they assert what the code does rather than
  what the AC says. Tell it: "derive expected values from the AC text, not
  from the implementation".
- Ask it to generate the *unhappy path* list first, then the tests.
- The `test-writer` subagent can draft tests for a whole module in the
  background while you continue implementing.
- The `testing` rule in `.cursor/rules/` enforces the naming and
  determinism standards automatically on files under `tests/` and `*.test.*`.
- To check requirement coverage: "Compare `test-plan.md` with the ACs in
  `prd.md` and list any AC without a passing test."

## Exit criteria (G4)

- CI: unit tests green, coverage threshold met.
- `test-plan.md` complete; no AC without a test or documented manual
  verification.
- No skipped or `xfail` tests without an `OQ` or issue reference.
