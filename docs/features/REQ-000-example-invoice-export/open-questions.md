# Open Questions — REQ-000 — Invoice export to ledger

> **Worked example.** Shows a register after two batches with the requester.

Ambiguity register for this requirement. See
[docs/framework/03-ambiguity-handling.md](../../framework/03-ambiguity-handling.md).

## Summary

| Severity | Open | Answered / Accepted |
|----------|------|---------------------|
| Blocking | 0 | 3 |
| Non-blocking | 1 | 1 |
| Cosmetic | 0 | 0 |

## Register

### OQ-1 — Export trigger: manual, scheduled, or on approval?

| | |
|---|---|
| **Stage raised** | intake |
| **Type** | Question |
| **Severity** | Blocking |
| **Raised by / date** | Sam K., 2026-09-01 |
| **Owner** | Priya N. |
| **Status** | Answered |
| **Due** | 2026-09-03 |

**Ambiguous text (quoted):**
> "A button on the invoice list that sends everything approved to the ledger."

**Question / assumption:** Is a manual trigger actually wanted, or is that
just the familiar shape? Timing affects dual control, error handling, and
whether analysts need a screen at all.

**Options considered:**

1. Manual button — analyst controls timing; still a manual step each cycle.
2. Nightly schedule — zero manual effort; failures surface next morning.
3. On approval, per invoice — fastest posting; many small API calls; harder
   to reconcile.

**Recommended:** Option 2, with a manual "run now" for month-end.

**Answer (verbatim, by whom, date):** "Nightly is fine as long as I can
kick it off manually on the last two working days of the month." — Priya N.,
2026-09-02

**Folded into:** prd.md FR-1, FR-2, AC-1, AC-2

---

### OQ-2 — LedgerCo API rate limits and batch size

| | |
|---|---|
| **Stage raised** | intake |
| **Type** | Question |
| **Severity** | Blocking |
| **Raised by / date** | Sam K., 2026-09-01 |
| **Owner** | Dev lead (Ana R.) via IT Vendor Management |
| **Status** | Answered |
| **Due** | 2026-09-05 |

**Ambiguous text (quoted):**
> "its REST API is available but rate-limited"

**Question / assumption:** Actual limits determine whether 300 invoices
can post in one run and whether batching is needed.

**Options considered:**

1. Limits generous → single nightly run, no batching.
2. Limits tight → batch with backoff; run may span hours.

**Recommended:** Design for option 2 regardless; cheap insurance.

**Answer (verbatim, by whom, date):** "60 requests/minute, max 100 lines per
journal call." — LedgerCo support ticket #4471, 2026-09-04

**Folded into:** prd.md NFR-2, §7 edge cases; technical-plan.md §3

---

### OQ-3 — Credit notes in phase 1?

| | |
|---|---|
| **Stage raised** | intake |
| **Type** | Assumption |
| **Severity** | Blocking |
| **Raised by / date** | Sam K., 2026-09-01 |
| **Owner** | Priya N. |
| **Status** | Accepted |
| **Due** | 2026-09-03 |

**Ambiguous text (quoted):**
> "download about 300 approved invoices"

**Question / assumption:** `[ASSUMED: phase 1 covers invoices only — OQ-3]`.
Credit notes reverse sign and have different ledger accounts.

**Options considered:**

1. Invoices only (phase 1), credit notes as REQ-00x later.
2. Both now — adds ~30 % scope and a second mapping.

**Recommended:** Option 1; credit notes are ~5 % of volume.

**Answer (verbatim, by whom, date):** "Agreed, invoices first." — Priya N.,
2026-09-02

**Folded into:** prd.md NG1; §14

---

### OQ-4 — What does "dual control" mean for an automated transfer?

| | |
|---|---|
| **Stage raised** | prd |
| **Type** | Question |
| **Severity** | Non-blocking |
| **Raised by / date** | Sam K., 2026-09-03 |
| **Owner** | Priya N. (with Internal Audit) |
| **Status** | Answered |
| **Due** | 2026-09-10 |

**Question / assumption:** Audit requires dual control. For an automated
job, is the existing invoice approval the first control and the export
log the second, or must a second person approve the export batch?

**Options considered:**

1. Approval + immutable export log satisfies audit.
2. Second-person release of each nightly batch before posting.

**Recommended:** Option 1; confirm with Internal Audit.

**Answer (verbatim, by whom, date):** "Approval plus a tamper-evident export
log is sufficient." — Internal Audit (J. M.), 2026-09-08

**Folded into:** prd.md FR-5, NFR-6, AC-6

---

### OQ-5 — Failure notification channel

| | |
|---|---|
| **Stage raised** | prd |
| **Type** | Assumption |
| **Severity** | Non-blocking |
| **Raised by / date** | Sam K., 2026-09-03 |
| **Owner** | Priya N. |
| **Status** | Open |
| **Due** | 2026-09-12 |

**Question / assumption:**
`[ASSUMED: failures are emailed to the Finance Ops shared mailbox — OQ-5]`.
Alternative is a Slack channel or an in-app exceptions list.

**Recommended:** Email; already monitored daily. Proceeding on this default.

**Answer (verbatim, by whom, date):** —

**Folded into:** prd.md FR-4 (marked ASSUMED)

---

## Batches sent to requester

| Batch | Date | Items | Returned |
|-------|------|-------|----------|
| 1 | 2026-09-01 | OQ-1, OQ-3 | 2026-09-02 |
| 2 | 2026-09-03 | OQ-4, OQ-5 | OQ-4 on 2026-09-08; OQ-5 pending |
