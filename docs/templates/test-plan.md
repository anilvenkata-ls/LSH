# Test Plan — REQ-nnn — <Short title>

| | |
|---|---|
| **ID** | REQ-nnn |
| **PRD** | [prd.md](prd.md) v1.0 |
| **Technical plan** | [technical-plan.md](technical-plan.md) |
| **Author** | Developer |
| **Status** | Draft / Complete (G4) |
| **How to run** | `<command>` — see feature-doc.md §7 |
| **Coverage (changed files)** | nn % (target 80 %) — CI link |

## 1. Acceptance criteria coverage

Every AC from the PRD has a row. Status is one of *Passing*, *Failing*,
*Not yet written*, *Verified manually (by, date)*, *Deferred (OQ/REQ ref)*.

| AC | Type | Test name(s) / location | Status | Notes |
|----|------|-------------------------|--------|-------|
| AC-1 | unit | `test_ac1_…` in `tests/unit/…` | Passing | |
| AC-2 | integration | | | |
| AC-3 | manual | UAT script step 4 | Verified manually (name, date) | |

## 2. Unhappy-path and edge-case tests

Not tied to a single AC but required by the framework (see ambiguity
checklist section C).

| Scenario | Component | Test name | Status |
|----------|-----------|-----------|--------|
| Empty input | | | |
| Maximum / boundary input | | | |
| Duplicate submission (idempotency) | | | |
| Downstream dependency failure | | | |
| Permission denied | | | |
| Concurrent use | | | |
| Locale / time zone | | | |

## 3. Non-functional verification

| NFR | How measured | Result | Status |
|-----|--------------|--------|--------|
| NFR-1 | | | |

## 4. Test data and fixtures

| Fixture | Represents | Location | Source / how generated |
|---------|-----------|----------|------------------------|
| | | | |

## 5. Manual / UAT script

For ACs marked *manual*: numbered steps, expected result, who performs,
environment.

| # | Step | Expected | Performed by | Date | Result |
|---|------|----------|--------------|------|--------|
| 1 | | | | | |

## 6. Known gaps

Anything not tested and why, each with an `OQ` or follow-up `REQ`.

---

## Gate G4 — Tests green

- [ ] CI unit test job green
- [ ] Coverage on changed files ≥ target
- [ ] Every AC has a row with status Passing or Verified manually
- [ ] Unhappy-path table complete for each component touched
- [ ] No skipped / xfail tests without an `OQ` or issue reference
- [ ] No test asserts an unaccepted assumption
- [ ] Test names carry AC IDs
