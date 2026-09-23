# Technical Plan — REQ-nnn — <Short title>

| | |
|---|---|
| **ID** | REQ-nnn |
| **PRD** | [prd.md](prd.md) v1.0 |
| **Author** | Developer |
| **Reviewer** | Second developer (≠ author) |
| **Status** | Draft / In review / Approved (G2) — set the cell to exactly `Approved (G2)` when passed; CI reads it |
| **Approved on** | YYYY-MM-DD, PR comment link |
| **Size (revised)** | S / M / L / XL |
| **Branch / PR** | `feature/REQ-nnn-slug` — PR #… |

## 1. Approach

Three to six sentences on the shape of the solution and the main
alternatives rejected (link ADRs for anything that outlives this feature).

## 2. Traceability

Every FR and AC in the PRD must appear. Anything not in the PRD must not.

| PRD item | Plan step(s) | Test(s) (fill in at stage 6) |
|----------|--------------|------------------------------|
| FR-1 / AC-1 | 2, 3 | |
| FR-2 / AC-2, AC-3 | 4 | |
| NFR-1 | 5 | |

## 3. Affected areas

| Area | Files / modules / tables | Change |
|------|--------------------------|--------|
| Backend | | |
| Data | | |
| Frontend | | |
| Config / infra | | |
| Third-party | | |
| New dependencies | name, version, why | |

## 4. Interfaces

New or changed endpoints, events, CLI, UI routes. Request/response shapes.
Backward compatibility statement.

## 5. Data changes

Migrations (order, idempotency, duration on prod-sized data), backfills,
retention, and the rollback for each.

## 6. Implementation steps

Small, independently reviewable steps; each becomes one or more commits.
Tick as completed. `/implement` resumes from the first unticked step.

- [ ] **Step 1 — <title>.** What changes; done when …
- [ ] **Step 2 — <title>.** …
- [ ] **Step 3 — <title>.** …

## 7. Test strategy

| AC | Type (unit / integration / contract / manual) | Notes (fixtures, doubles, data) |
|----|-----------------------------------------------|---------------------------------|
| AC-1 | unit | |
| AC-2 | integration | sandbox ledger API |

Unhappy paths to cover explicitly:

Coverage target for changed files: 80 % (or justify a different number).

## 8. Documentation impact

- [ ] `feature-doc.md` sections: …
- [ ] Module README: …
- [ ] API reference: …
- [ ] ADR: …
- [ ] Runbook: …

## 9. Security and privacy

Authn/authz points, input validation, secrets handling, PII touched, audit
logging.

## 10. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| | | | |

## 11. Rollout and rollback

Feature flag (name, default), phased rollout, migration ordering,
compatibility window, rollback steps.

## 12. Out of scope / deferred

Items deliberately not done, each with a follow-up `REQ` or a note that the
requester agreed to drop it.

## 13. Open questions raised at plan stage

Links to `OQ-n` entries created while planning.

## 14. Change log

| Date | Author | Change | Re-approval needed? |
|------|--------|--------|---------------------|
| | | Initial | — |

---

## Gate G2 — Plan approved

- [ ] Traceability table covers every FR/AC/NFR in the PRD
- [ ] No step depends on an Open Blocking `OQ`
- [ ] Reuses existing modules; no duplicate implementations
- [ ] Data changes have rollback
- [ ] Interface compatibility stated
- [ ] Security section complete
- [ ] Test strategy covers failure paths
- [ ] Steps small enough to review (< ~400 changed lines each)
- [ ] Documentation impact listed
- [ ] No gold-plating (nothing here is absent from the PRD)
- [ ] `plan-reviewer` subagent run; findings addressed
- [ ] Human reviewer commented "Plan approved" on the PR
- [ ] Label moved to `stage:implementation`
