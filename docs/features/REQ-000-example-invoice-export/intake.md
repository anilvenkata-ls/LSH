# REQ-000 — Invoice export to ledger

> **Worked example.** This folder shows what stage 1–2 artifacts look like
> when filled in. It is not a real requirement; do not build it.

| | |
|---|---|
| **ID** | REQ-000 |
| **Requester** (single accountable person) | Priya N., Finance Operations Lead, priya@example.com |
| **Product owner / BA** | Sam K. |
| **Date raised** | 2026-09-01 |
| **Type** | New capability |
| **Urgency** | Hard deadline 2026-11-30 — SOX audit finding must be closed before Q4 close |
| **Size guess** | M — one new export path, one external API, no UI redesign |
| **Source** | Issue #12 (Business requirement form) |
| **Status** | Accepted (G0) |

## Problem statement (in the requester's words)

> "Every month we download about 300 approved invoices from the portal one
> by one and re-type the header and line totals into the ledger. It takes
> two of us most of three days, and last quarter audit found 6 keying errors
> out of ~900. The auditors want a system-to-system transfer."

## Business value

- ~20 person-hours/month recovered in Finance Ops.
- Closes SOX finding FIN-2026-03 (manual re-keying without dual control).
- Removes a ~2 % keying error rate that causes month-end reconciliation
  rework.

## Who is affected

| Role / group | Approx. count | How they are affected |
|--------------|---------------|-----------------------|
| Finance Ops analysts | 2 | Perform the re-keying today; would trigger/monitor the export instead |
| Finance controller | 1 | Reviews reconciliation exceptions |
| Internal audit | 2 | Need evidence of controlled transfer |

## Current process (as-is)

1. Analyst filters portal to "Approved, not yet posted" invoices.
2. Opens each invoice, copies supplier, date, total, tax, cost centre into
   the ledger's manual journal screen.
3. Marks the invoice "posted" in a shared spreadsheet.
4. Controller reconciles ledger vs. spreadsheet at month end.

## Desired outcome (to-be, outcome not solution)

Approved invoices reach the ledger without manual re-keying, with a record
of what was transferred and when, and Finance can see anything that failed
to transfer.

## Success measure

Manual re-keying time drops from ~20 h/month to under 2 h/month (exceptions
only); keying error rate for exported invoices is 0; audit finding closed.

## Constraints

- Deadline / regulatory: SOX finding, 2026-11-30.
- Systems: ledger is the vendor-hosted "LedgerCo" system; its REST API is
  available but rate-limited (`[UNKNOWN]` exact limits — OQ-2).
- Budget or capacity: no new vendor contracts.
- Security / compliance: invoice data includes supplier bank details —
  financial PII; dual control required for anything posted.

## Requester's suggested approach (optional, non-binding)

"A button on the invoice list that sends everything approved to the ledger."

## Known unknowns

- `[UNKNOWN]` Should export be triggered manually, on a schedule, or on
  approval? — OQ-1
- `[UNKNOWN]` LedgerCo API rate limits and batch size — OQ-2
- `[ASSUMED: phase 1 covers invoices only, not credit notes — OQ-3]`
- `[UNKNOWN]` What "dual control" means for an automated transfer — OQ-4

## Related

- Previous attempt: 2024 CSV upload was abandoned (LedgerCo removed CSV
  import).
- Dependency: LedgerCo API credentials owned by IT Vendor Management.

---

## Gate G0 — Intake accepted

- [x] Single accountable requester named and available for questions
- [x] Problem statement confirmed by requester (read back, not just "looks fine")
- [x] Business value stated and, where possible, quantified
- [x] Success measure is observable
- [x] Type, urgency, and size guess set
- [x] Feature folder created; GitHub issue opened and labelled `stage:intake`

Accepted by: Sam K. (product owner) on 2026-09-02
