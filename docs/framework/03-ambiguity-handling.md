# Ambiguity Handling

Ambiguity is the single largest source of rework in this pipeline: a vague
requirement becomes a guessed PRD, a guessed plan, wrong code, and tests that
prove the wrong thing. This document defines **where ambiguity is detected,
how it is classified, who resolves it, and what is allowed to proceed while
questions are open**.

## Principles

1. **Detect early, resolve at the cheapest stage.** A question costs minutes
   at intake, hours at PRD, days after code is written.
2. **Never silently guess.** Any interpretation made by a person or by Cursor
   must be written down as an `[ASSUMED: …]` marker in the document and an
   entry in `open-questions.md`. Unmarked guesses are treated as defects.
3. **Questions go to the requester in batches, not one at a time.** Each
   `/clarify` run produces a batch; the product owner takes the batch to the
   business user.
4. **Blocking questions stop the gate; assumptions do not.** An assumption
   that the requester has *acknowledged* may proceed. An unacknowledged one
   may not.
5. **The ambiguity register is an artifact, not a chat.** Answers are written
   into `open-questions.md` and folded into the PRD; Slack threads and
   meeting memory do not count.

## The ambiguity register — `open-questions.md`

One row per question, using `docs/templates/open-questions.md`:

| Field | Meaning |
|-------|---------|
| `OQ-n` | Stable ID, referenced from PRD / plan / PR |
| Stage raised | intake / prd / plan / implementation / testing / release |
| Type | *Question* (need an answer), *Assumption* (we chose an interpretation), *Change request* (post-approval) |
| Severity | **Blocking**, **Non-blocking**, **Cosmetic** (see below) |
| Question / assumption | Precise wording; quote the ambiguous sentence |
| Options considered | The 2–3 plausible interpretations, with consequences |
| Recommended | The option the author proposes and why |
| Owner | Who must answer (usually the business user) |
| Status | Open / Answered / Accepted (assumption acknowledged) / Withdrawn |
| Answer | Verbatim answer, who gave it, date |
| Folded into | Which PRD/plan section was updated |

### Severity rules

| Severity | Definition | Gate effect |
|----------|-----------|-------------|
| **Blocking** | Different plausible answers lead to *materially different* scope, data model, integrations, or acceptance criteria | Gate cannot pass while any Blocking item is Open |
| **Non-blocking** | Affects details of behaviour or UX but not architecture; a documented default exists | Gate may pass if the item is recorded with a *Recommended* default and the requester has been notified |
| **Cosmetic** | Wording, labels, ordering, colours | Resolve any time before release |

If in doubt, mark Blocking. Downgrading requires the product owner's
initials in the register.

## Ambiguity checklist — what `/clarify` looks for

The `/clarify` skill applies this list against the PRD (and, later, the plan).
Humans reviewing a PRD should use the same list.

### A. Language

- Vague quantifiers: *fast, many, large, soon, regularly, some, most, usually*.
  → Ask for a number or a bound.
- Modal ambiguity: *should, could, may, might*. → Replace with *must* /
  *must not* / *may (optional)*.
- Undefined terms and acronyms. → Add to the PRD glossary.
- Pronouns without a clear referent (*it, they, this*).
- "Etc.", "and so on", "such as" without a closed list.
- "And/or" inside a single requirement. → Split.

### B. Scope

- Which users / roles / tenants / regions are in and out?
- Which channels (web, mobile, API, batch, email)?
- Is this replacing existing behaviour or adding alongside it? What happens to
  the old path?
- Is there a phase 1 / phase 2 split hiding inside the request?

### C. Behaviour and edge cases

- Empty input, maximum input, duplicates, unicode, time zones, locales,
  currencies.
- Failure paths: what does the user see when the downstream system is down?
- Concurrency: two users doing this at the same time.
- Idempotency: the same action submitted twice.
- Permissions: who is *not* allowed to do this, and what do they see?
- Undo / cancel / partial completion.

### D. Data

- Source of truth for each field. Is it derived or entered?
- Validation rules, formats, ranges, required vs. optional.
- Retention, deletion, audit trail, PII / regulatory classification.
- Historic data: does this apply retroactively?

### E. Non-functional

- Volume (records, users, requests) now and in 12 months.
- Latency and throughput targets.
- Availability window; is downtime for migration acceptable?
- Accessibility, browser/device support, localisation.
- Security: authentication, authorisation, secrets, encryption.

### F. Integration and dependencies

- External systems touched; who owns them; are their APIs stable?
- Other teams or features that must land first.
- Feature flags, gradual rollout, or big-bang?

### G. Success and acceptance

- Is every acceptance criterion observable and falsifiable?
- Is the success metric measurable after release, and by whom?
- Who performs acceptance testing and where (staging? production?)?

### H. Priority and trade-offs

- If we can only ship half of this, which half?
- Deadline: hard (regulatory / contractual) or soft?
- Preferred trade-off when quality, scope, and date conflict.

## Resolution flow

```
Detect (any stage) ─▶ Record OQ-n with severity ─▶ Batch to owner ─▶ Answer recorded
        │                                                                  │
        └─── If no answer within SLA: escalate to product owner ◀──────────┘
                     │
                     ├─ Blocking: gate stays closed; work may continue only on unaffected parts
                     └─ Non-blocking: proceed on Recommended default; mark [ASSUMED] in PRD/plan
```

**Answer SLA:** 2 working days for Blocking, 5 for Non-blocking. Owners are
named individuals, not teams. If the SLA lapses, the product owner either
obtains the answer, reassigns the owner, or converts the question into an
*Accepted assumption* with their own name attached (taking responsibility).

## Working while questions are open

Allowed:
- Writing the parts of the PRD, plan, or code that no open Blocking question
  affects. Note the dependency in the artifact: `Depends on OQ-4`.
- Prototyping to *inform* an answer, clearly labelled as throwaway.

Not allowed:
- Passing G1 or G2 with an Open Blocking item.
- Writing tests that encode an unacknowledged assumption as expected
  behaviour.
- Merging to `main` with any `[ASSUMED]` marker that has no matching
  *Accepted* register entry. The `pr-gates` CI job flags these.

## Ambiguity at later stages

- **Plan stage:** the developer often discovers questions the PRD author could
  not (e.g. "the ledger API only accepts one currency per call"). Same
  register, stage = `plan`. If Blocking, G2 waits.
- **Implementation / testing:** questions here are usually signs of a thin
  PRD. Record them anyway; if the answer changes an AC, bump the PRD version.
- **Release:** operational questions (who is on call, rollback owner) go in
  the release checklist rather than the register.

## How Cursor helps

- `/clarify` applies the checklist above and writes the register. It also
  proposes *Options considered* and a *Recommended* default for each, which
  makes the conversation with the business user much faster: they choose
  rather than invent.
- Plan mode in Cursor asks clarifying questions before producing a plan; the
  developer should copy any it raises about *requirements* (as opposed to
  code) into the register.
- The `workflow` rule instructs the agent to write `[ASSUMED: …]` whenever it
  fills a gap, and never to resolve an ambiguity by picking silently.
- Bugbot, via `.cursor/BUGBOT.md`, is told to flag `[ASSUMED]` markers and
  `TODO` comments that reference no `OQ-n`.
