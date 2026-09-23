---
name: intake
description: Stage 1 — turn a raw business request (email, Slack text, issue, notes) into docs/features/REQ-nnn-slug/intake.md using the intake template, marking gaps [UNKNOWN] and interpretations [ASSUMED]. Use when a new requirement arrives or the user says "intake", "new requirement", or pastes a business request.
---

# /intake — Requirements intake

Process reference: `docs/framework/01-requirements-intake.md`.
Template: `docs/templates/requirement-intake.md`.

## Inputs

- The raw request: pasted text in the chat, an attached file, or a GitHub
  issue body the user points at.
- Existing `docs/features/` folders (to allocate the next `REQ` ID).

## Procedure

1. **Allocate the ID.** List `docs/features/`, find the highest `REQ-nnn`,
   use the next number. If the user supplies an ID, use theirs. Propose a
   2–4 word lowercase-hyphen slug; ask only if the request is too vague to
   name.
2. **Create the folder** `docs/features/REQ-nnn-slug/` and copy the template
   to `intake.md`.
3. **Fill the template from the request.** Quote the requester's words in
   *Problem statement*. Do not invent a solution; if the request contains one,
   put it under *Requester's suggested approach*.
4. **Mark gaps honestly.**
   - Information not present → `[UNKNOWN]` in that field.
   - Something you inferred → `[ASSUMED: …]` and a bullet under *Known
     unknowns*.
   - Do not leave fields blank silently.
5. **Classify** Type, Urgency, Size guess, with a one-line reason for the
   size.
6. **Draft the first `open-questions.md`** from the template with one `OQ`
   per `[UNKNOWN]` / `[ASSUMED]` item, severity set per
   `docs/framework/03-ambiguity-handling.md` (default to Blocking for
   anything about scope, users, data, or success measure).
7. **Report back** in chat:
   - Path of the new folder.
   - The G0 checklist with what is already satisfiable and what needs the
     requester.
   - The list of questions to send the requester, grouped, ready to paste
     into an email.

## Do not

- Write a PRD, plan, or code. Stop at intake.
- Assign a size larger than M without saying why.
- Merge several distinct requests into one `REQ`; propose a split instead.
