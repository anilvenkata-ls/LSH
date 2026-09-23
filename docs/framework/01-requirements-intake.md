# Stage 1 — Requirements Intake

**Input:** a request from a business user, in any form (email, Slack message,
meeting notes, a GitHub issue created with the "Business requirement" form).
**Output:** `docs/features/<ID>-<slug>/intake.md`, complete enough to pass G0.
**Owner:** Product owner / BA.
**Cursor:** `/intake` — paste the raw request and the skill drafts `intake.md`.

## Purpose

Capture *what the business needs and why* in the business user's own terms,
before anyone proposes a solution. Most downstream ambiguity comes from
skipping this step and jumping to "build a button that…".

## Steps

1. **Allocate an ID.** Next free `REQ-nnn` (check `docs/features/`). Pick a
   slug of 2–4 words. Create the folder.
2. **Run `/intake`** in Cursor with the raw request pasted in. The skill fills
   `docs/templates/requirement-intake.md` and marks anything it had to guess
   with `[ASSUMED]` or `[UNKNOWN]`.
3. **Verify with the requester.** Send them the drafted `intake.md`. Ask them
   to correct the *Problem statement* and *Business value* sections in their
   own words. Do not accept "yes looks fine" — ask them to read those two
   sections back to you.
4. **Classify.** Set *Type* (new capability / change / fix / compliance),
   *Urgency*, and *Size guess* (S/M/L/XL). Size is a guess and will be
   revised at the plan stage; it only decides how heavy the PRD needs to be.
5. **Pass G0.** Tick the checklist at the bottom of `intake.md`. Open the
   GitHub issue if it does not exist and label it `stage:intake`.

## What "good" looks like

| Section | Good | Not good |
|---------|------|----------|
| Problem statement | "Finance re-keys 300 invoices a month from the portal into the ledger, ~20 hours, with ~2% error rate." | "We need an export feature." |
| Business value | "Saves ~20 h/month; removes a SOX finding due in Q4." | "It would be nice." |
| Who is affected | Named roles and approximate counts | "Users" |
| Success measure | Something observable after release | "People are happier" |
| Constraints | Deadline, regulation, system boundaries, budget | Left blank |

## Right-sizing

- **S (< 2 days):** intake + a one-page PRD. Plan can be a paragraph in the PR.
- **M (2–10 days):** full templates.
- **L / XL:** full templates, plus an ADR for any architectural decision and a
  split into multiple `REQ`s if it cannot ship in one PR.

## Common intake mistakes

- Recording the requester's *proposed solution* as the requirement. Write the
  solution under *Requester's suggested approach* so it is preserved but not
  binding.
- Missing the "instead of what?" — what happens today without this feature.
- Not naming a single accountable requester who can answer questions and
  sign off. Committees do not sign off PRDs.
