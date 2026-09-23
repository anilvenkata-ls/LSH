# PRD — REQ-000 — Invoice export to ledger

> **Worked example.** Abbreviated PRD showing IDs, must/must-not wording,
> edge cases, and how `[ASSUMED]` / `OQ` references appear. Sections 4, 5,
> 10, 12, 13 are shortened.

| | |
|---|---|
| **ID** | REQ-000 |
| **Version** | 1.0 (Approved) |
| **Author** | Sam K. |
| **Requester** | Priya N. |
| **Intake** | [intake.md](intake.md) |
| **Open questions** | [open-questions.md](open-questions.md) |
| **Status** | Approved |
| **Approved by** | Priya N., 2026-09-09 |
| **Size** | M |

## 1. Summary

Approved invoices in the portal are posted to the LedgerCo ledger
automatically each night, with a manual "run now" for month-end, an
immutable export log for audit, and email notification of failures. This
removes ~20 h/month of re-keying and closes SOX finding FIN-2026-03.

## 2. Goals

1. G1 — Eliminate manual re-keying of approved invoices.
2. G2 — Provide audit evidence of every transfer.
3. G3 — Surface transfer failures to Finance Ops within one working day.

## 3. Non-goals

- NG1 — Credit notes (deferred; OQ-3 accepted; future REQ).
- NG2 — Changes to the invoice approval workflow.
- NG3 — Two-way sync (ledger → portal).
- NG4 — Replacing the month-end reconciliation report.

## 4. Users and roles

| Role | Description | Permissions relevant to this feature |
|------|-------------|--------------------------------------|
| Finance Ops analyst | Monitors exports, triggers month-end run | Trigger export; view export log |
| Finance controller | Reviews exceptions | View export log |
| System (scheduler) | Runs nightly job | Post to ledger |

## 5. User stories / scenarios

- **US-1** — As an analyst, I want approved invoices posted overnight so I
  no longer re-key them.
- **US-2** — As an analyst, I want to trigger a run on demand at month-end
  so nothing waits for the schedule.
- **US-3** — As a controller, I want to see which invoices failed to post
  and why, so I can resolve exceptions.
- **US-4** — As an auditor, I want an unalterable record of what was posted,
  when, and from which approval.

## 6. Functional requirements

| ID | Requirement | Stories | Priority | Notes / OQ refs |
|----|-------------|---------|----------|-----------------|
| FR-1 | The system must post every invoice in status *Approved, not posted* to the ledger in a nightly run at 02:00 local. | US-1 | Must | OQ-1 |
| FR-2 | An analyst must be able to trigger an additional run at any time; concurrent runs must not occur. | US-2 | Must | OQ-1 |
| FR-3 | Each invoice must be posted at most once (idempotent by invoice ID). | US-1, US-4 | Must | |
| FR-4 | Failed postings must be listed with the ledger error and emailed to the Finance Ops mailbox after each run. `[ASSUMED: email to shared mailbox — OQ-5]` | US-3 | Must | OQ-5 |
| FR-5 | Every posting attempt must be written to an append-only export log with invoice ID, approval ID, approver, timestamp, ledger journal ID, and outcome. | US-4 | Must | OQ-4 |
| FR-6 | Invoices that fail must remain *Approved, not posted* and be retried in the next run, up to 3 runs, then flagged *Needs attention*. | US-3 | Must | |
| FR-7 | The system may post invoices in batches of up to 100 lines per ledger call. | US-1 | May | OQ-2 |

## 7. Behaviour details and edge cases

| FR | Situation | Expected behaviour |
|----|-----------|--------------------|
| FR-1 | No approved invoices | Run completes, log records "0 posted", no email sent |
| FR-2 | Run triggered while one is in progress | Second request rejected with "Run already in progress (started hh:mm)" |
| FR-3 | Same invoice appears in two runs (e.g. status not updated after crash) | Second attempt detects existing journal ID in log and skips |
| FR-4 | LedgerCo API unavailable for the whole run | All invoices marked failed with "ledger unavailable"; single summary email; retry next run |
| FR-6 | Invoice edited after approval but before posting | Post is skipped; invoice flagged *Needs attention* with reason "modified after approval" |
| FR-7 | Invoice with > 100 lines | Split across calls; all-or-nothing — if any part fails, whole invoice is failed and any posted parts reversed |
| all | Rate limit (429) from ledger | Back off per `Retry-After`; run may exceed one hour; must finish before 07:00 or stop and report remaining |

## 8. Data requirements

| Field / entity | Read or written | Source of truth | Validation | Classification | Retention |
|----------------|-----------------|-----------------|------------|----------------|-----------|
| Invoice header (id, supplier, date, totals, tax, cost centre) | Read | Portal invoices table | As already validated at approval | Financial | Existing |
| Supplier bank details | Not read | — | — | Financial PII | — |
| Export log row | Written | New `export_log` table | Append-only; no updates/deletes | Financial / audit | 7 years |
| Invoice status *posted* / *Needs attention* | Written | Portal invoices table | Enum | — | Existing |

Migrations: new `export_log` table. No backfill; historic manual postings are
out of scope.

## 9. Non-functional requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-1 | Performance | 500 invoices post within 60 minutes under normal API conditions |
| NFR-2 | Rate limits | Respect 60 req/min and 100 lines/call (OQ-2) |
| NFR-3 | Availability | Nightly run failure must not affect portal availability |
| NFR-4 | Security | Ledger credentials stored in the secrets manager; never logged |
| NFR-5 | Authorisation | Only *Finance Ops analyst* role may trigger a run |
| NFR-6 | Auditability | Export log append-only at database level (OQ-4) |

## 10. Interfaces and integrations

LedgerCo REST API — journals endpoint; owned by LedgerCo; credentials via IT
Vendor Management. Portal scheduler for the nightly job. Email service for
notifications.

## 11. Acceptance criteria

| ID | FR(s) | Acceptance criterion | Verification |
|----|-------|----------------------|--------------|
| AC-1 | FR-1 | Given 3 approved-unposted invoices at 02:00, when the nightly run executes, then all 3 have status *posted* and a journal ID in the log | integration |
| AC-2 | FR-2 | Given a run in progress, when an analyst triggers another, then the request is rejected with the in-progress message and no second run starts | unit |
| AC-3 | FR-3 | Given an invoice already logged with a journal ID, when a run selects it again, then it is skipped and the log records "skipped: already posted" | unit |
| AC-4 | FR-4, FR-6 | Given the ledger returns an error for one invoice, when the run ends, then the invoice remains unposted, the log records the error, and one email lists it | unit + integration |
| AC-5 | FR-6 | Given an invoice has failed in 3 consecutive runs, when the third fails, then its status becomes *Needs attention* | unit |
| AC-6 | FR-5, NFR-6 | Given any posting attempt, when it completes, then an export_log row exists and attempts to UPDATE or DELETE it are rejected by the database | integration |
| AC-7 | FR-7 | Given an invoice with 250 lines, when posted, then it is sent in 3 calls and either all succeed or the invoice is marked failed with partial posts reversed | unit |
| AC-8 | NFR-5 | Given a user without the analyst role, when they call the trigger endpoint, then they receive 403 and no run starts | unit |

## 12. Rollout and success measurement

Feature flag `invoice_export.enabled` (default off); enable for one week in
"dry run" mode (log only, no posting) before live. Success measure read at
end of first full month by Finance Ops from time logs.

## 13. Glossary

| Term | Meaning |
|------|---------|
| Posted | Invoice has a ledger journal ID recorded in the export log |
| Run | One execution of the export job, scheduled or manual |

## 14. Assumptions

| OQ | Assumption | Status |
|----|-----------|--------|
| OQ-3 | Phase 1 covers invoices only | Accepted |
| OQ-5 | Failures emailed to Finance Ops shared mailbox | Open (Non-blocking; proceeding on default) |

## 15. Change log

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 0.1 | 2026-09-03 | Sam K. | Initial draft |
| 0.2 | 2026-09-08 | Sam K. | Folded OQ-1..OQ-4 answers |
| 1.0 | 2026-09-09 | Sam K. | Approved by Priya N. |

---

## Gate G1 — PRD approved

- [x] No Open **Blocking** items in `open-questions.md`
- [x] All assumptions listed in §14 are *Accepted* by the requester (OQ-5 is Non-blocking, requester notified)
- [x] Every FR has at least one AC; every AC is testable
- [x] Goals and non-goals both present
- [x] NFRs numeric where applicable
- [x] Data requirements complete, classification noted
- [x] Failure / edge behaviour specified for each FR where relevant
- [x] No `TBD` remaining; open items are `OQ-n` references
- [x] Requester sign-off recorded in the header
- [x] Issue label moved to `stage:prd-approved`
