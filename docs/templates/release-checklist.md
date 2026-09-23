# Release Checklist — REQ-nnn — <Short title>

| | |
|---|---|
| **ID** | REQ-nnn |
| **PR** | #… |
| **Prepared by** | Developer |
| **Release owner** | Name |
| **Target window** | Date / time / environment |
| **Status** | In progress / Ready to deploy (G5) |

Mark each item **Done**, **Missing**, or **N/A** (with reason). Link
evidence.

## 1. Scope confirmation

| Item | Status | Evidence |
|------|--------|----------|
| Every FR / AC delivered or explicitly deferred with a `REQ` | | |
| `open-questions.md` has no `Open` items of any severity | | |
| PRD version built matches the approved version | | |
| Technical plan change log has no un-re-approved changes | | |

## 2. Quality

| Item | Status | Evidence |
|------|--------|----------|
| CI green on the final commit | | |
| Coverage on changed files ≥ target | | |
| Bugbot comments resolved or answered | | |
| Human code review approved (G3) | | |
| Security review done if plan §9 flagged it | | |
| NFRs measured (performance, volume) | | |

## 3. Deployment

| Item | Status | Evidence |
|------|--------|----------|
| Migration order documented; migrations idempotent | | |
| Config / secrets present in every target environment | | |
| Feature flag name and default recorded | | |
| Backward compatible with previous version during rollout | | |
| Deployment mechanism / runbook linked (see CONTRIBUTING.md → Deploying) | | |

## 4. Rollback

| Item | Status | Evidence |
|------|--------|----------|
| Exact rollback steps written | | |
| Data rollback for migrations (or "forward-only" agreed) | | |
| Who executes rollback and expected duration | | |

## 5. Observability

| Item | Status | Evidence |
|------|--------|----------|
| Logs include feature identifier | | |
| Metrics / alerts for new failure paths | | |
| Dashboard link | | |
| "Healthy in the first hour" definition | | |

## 6. Communication

| Item | Status | Evidence |
|------|--------|----------|
| Release notes line written | | |
| Support / ops briefed | | |
| Business user informed of go-live | | |
| Customer-facing notice (if any) | | |

## 7. Documentation

| Item | Status | Evidence |
|------|--------|----------|
| `feature-doc.md` reflects as-built | | |
| README / API reference updated | | |
| ADRs recorded | | |
| Runbook entry added if operational behaviour changed | | |
| Code documentation standards met (no bare TODOs, public APIs documented) | | |

## 8. Business acceptance

| Item | Status | Evidence |
|------|--------|----------|
| Manual / UAT rows in `test-plan.md` verified on staging | | |
| Business user acceptance recorded | Name, date | |

---

## Gate G5 — Ready to deploy

- [ ] All sections above Done or N/A with reason
- [ ] PR marked *Ready for review* and approved by release owner
- [ ] Label moved to `stage:ready-to-deploy`

| Sign-off | Name | Date |
|----------|------|------|
| Developer | | |
| Code reviewer | | |
| Business user | | |
| Release owner | | |
