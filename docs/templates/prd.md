# PRD — REQ-nnn — <Short title>

| | |
|---|---|
| **ID** | REQ-nnn |
| **Version** | 0.1 (Draft) → 1.0 (Approved) |
| **Author** | Product owner / BA |
| **Requester** | Business user |
| **Intake** | [intake.md](intake.md) |
| **Open questions** | [open-questions.md](open-questions.md) |
| **Status** | Draft / In review / Approved |
| **Approved by** | Business user name, YYYY-MM-DD |
| **Size** | S / M / L / XL |

## 1. Summary

Two or three sentences: the problem, who it is for, and what will be
different when this ships.

## 2. Goals

Numbered, outcome-oriented. Each goal should map to the success measure in
the intake.

1. G1 —
2. G2 —

## 3. Non-goals

Explicitly out of scope for this requirement. Anything a reasonable reader
might assume is included but is not.

- NG1 —
- NG2 —

## 4. Users and roles

| Role | Description | Permissions relevant to this feature |
|------|-------------|--------------------------------------|
| | | |

## 5. User stories / scenarios

Use *As a … I want … so that …* or a short narrative per scenario. Include
the primary path and the important alternative paths.

- **US-1** — As a …, I want …, so that ….
- **US-2** — …

## 6. Functional requirements

One requirement per row. No "and/or". Use *must* / *must not* / *may*.

| ID | Requirement | Stories | Priority (Must/Should/Could) | Notes / OQ refs |
|----|-------------|---------|------------------------------|-----------------|
| FR-1 | The system must … | US-1 | Must | |
| FR-2 | | | | |

## 7. Behaviour details and edge cases

For each FR where it matters: empty / max input, duplicates, concurrency,
permission denied, downstream failure, cancellation, time zones, locales.

| FR | Situation | Expected behaviour |
|----|-----------|--------------------|
| FR-1 | Downstream ledger API unavailable | Show "Export queued; you will be emailed when complete"; retry 3× with backoff (OQ-4 accepted) |

## 8. Data requirements

| Field / entity | Read or written | Source of truth | Validation | Classification (PII / financial / none) | Retention |
|----------------|-----------------|-----------------|------------|------------------------------------------|-----------|
| | | | | | |

Migrations, backfills, or historic-data implications:

## 9. Non-functional requirements

| ID | Category | Requirement (numeric where possible) |
|----|----------|--------------------------------------|
| NFR-1 | Performance | |
| NFR-2 | Volume / scale | |
| NFR-3 | Availability | |
| NFR-4 | Security / authz | |
| NFR-5 | Accessibility / localisation | |
| NFR-6 | Auditability | |

## 10. Interfaces and integrations

External systems, APIs, files, events touched; who owns them; constraints.

## 11. Acceptance criteria

Every FR has ≥ 1 AC. Written so a test can pass or fail it. Prefer
Given / When / Then.

| ID | FR(s) | Acceptance criterion | Verification (unit / integration / manual) |
|----|-------|----------------------|-------------------------------------------|
| AC-1 | FR-1 | Given …, when …, then … | unit |
| AC-2 | | | |

## 12. Rollout and success measurement

- Rollout approach (all users / by role / feature flag / phased):
- Success measure and how/when it will be read:
- Acceptance testing: who, where (staging/prod), when:

## 13. Glossary

| Term | Meaning |
|------|---------|
| | |

## 14. Assumptions

Every `[ASSUMED: …]` in this document, with its `OQ-n` and status.

| OQ | Assumption | Status (Open / Accepted) |
|----|-----------|--------------------------|
| | | |

## 15. Change log

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 0.1 | | | Initial draft |

---

## Gate G1 — PRD approved

- [ ] No Open **Blocking** items in `open-questions.md`
- [ ] All assumptions listed in §14 are *Accepted* by the requester
- [ ] Every FR has at least one AC; every AC is testable
- [ ] Goals and non-goals both present
- [ ] NFRs numeric where applicable
- [ ] Data requirements complete, classification noted
- [ ] Failure / edge behaviour specified for each FR where relevant
- [ ] No `TBD` remaining; open items are `OQ-n` references
- [ ] Requester sign-off recorded in the header
- [ ] Issue label moved to `stage:prd-approved`
