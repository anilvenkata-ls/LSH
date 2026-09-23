---
name: clarify
description: Ambiguity pass — scan a PRD, plan, or requirement text for vague, missing, or conflicting statements using the ambiguity checklist, and write/update open-questions.md with severity, options, and a recommended default. Use when the user says "clarify", "find ambiguities", "what's unclear", or before approving a PRD or plan.
---

# /clarify — Ambiguity detection and register

Process reference: `docs/framework/03-ambiguity-handling.md` (checklist
sections A–H and severity rules).
Template: `docs/templates/open-questions.md`.

## Inputs

- The document to scan: the open file, or `prd.md` / `technical-plan.md` in
  the feature folder, or text pasted in chat.
- Existing `open-questions.md` (do not duplicate existing `OQ`s; update them).

## Procedure

1. **Scan** the document against every checklist section:
   A Language · B Scope · C Behaviour/edge cases · D Data · E Non-functional ·
   F Integration · G Success/acceptance · H Priority/trade-offs.
   For each finding, quote the exact ambiguous text.
2. **Classify** each finding:
   - Type: Question / Assumption / Change request.
   - Severity: Blocking if plausible answers change scope, data model,
     integrations, or ACs; Non-blocking if a documented default exists;
     Cosmetic otherwise. When unsure, Blocking.
3. **Propose options and a recommendation.** Two or three plausible
   interpretations with consequences, and the one you recommend and why.
   This is what lets the business user *choose* instead of *invent*.
4. **Write the register.** Append new `OQ-n` blocks (next free number) to
   `open-questions.md`; update the summary table; set Owner to the requester
   for business questions and to the developer/tech lead for technical ones.
5. **Annotate the source document.** Where you found an ambiguity, insert
   `[ASSUMED: <recommended default> — OQ-n]` (for assumptions) or
   `(see OQ-n)` (for questions). Do not delete the original text.
6. **Report in chat:**
   - Count by severity.
   - The Blocking items in full (these stop the gate).
   - A ready-to-send batch for the requester: numbered questions with the
     options, in plain language, no jargon.
   - Whether the gate (G1 or G2) can currently pass.

## Rules

- Never resolve an ambiguity by silently picking an interpretation; always
  go through the register.
- Quote, don't paraphrase, the ambiguous text.
- Plain-language questions: the reader is a business user, not a developer.
- Re-running `/clarify` after answers are recorded must fold each Answered
  item into the document and set *Folded into*.
