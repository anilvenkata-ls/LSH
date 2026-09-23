---
name: document-code
description: Stage 7 / on demand — document code and create or refresh documentation. Adds module headers and public doc comments to the standard without changing behaviour, creates or updates feature-doc.md, module READMEs, and proposes ADRs per the documentation decision guide. Use when the user says "document this", "write docs", "create a doc for", "update the feature doc", or "add docstrings".
---

# /document-code — Code and feature documentation

Reference: `docs/framework/10-documentation.md` (catalogue, decision guide,
code-level standards).
Templates: `docs/templates/feature-doc.md`, `docs/templates/adr.md`.

## Determine the scope

In order of precedence: the user's explicit target → selected text → open
file → `@Branch (Diff with Main)` for the current feature. State the scope
before starting.

## Procedure

### A. Code-level documentation (never changes behaviour)

1. For each file in scope, add or repair the module header (purpose,
   `REQ-`, link to `feature-doc.md`).
2. For each public function/class/method/type: add or repair the doc
   comment (purpose, params with units/ranges, return, errors, notable
   behaviour, example if non-obvious). Match the language's idiom and the
   file's existing style.
3. Replace narrating comments with nothing, or with a why-comment if there
   is a why.
4. Convert bare `TODO`/`FIXME` to `TODO(OQ-n)` / `TODO(#issue)`; if no
   reference exists, create an `OQ` entry.
5. Make sure every config key/flag/env var read in scope has a one-line
   comment and appears in `feature-doc.md` §5.

### B. Feature documentation

1. If `feature-doc.md` is missing for the feature, create it from the
   template and fill §1–§5 from the plan and the code as built.
2. If it exists, update only the sections affected by the scope (interfaces,
   data, config, operations, dependencies, decisions, limitations) and add a
   change-log row.
3. Where the built design differs from `technical-plan.md`, document the
   as-built version and note the divergence in §9 Decisions.

### C. Other documents — apply the decision guide

Use the "Create a document when needed" table in
`docs/framework/10-documentation.md`:

- New top-level module/package → module README (sections: purpose, key
  types, how to use, how to test, owner).
- New/changed public interface → API reference entry.
- New operational failure mode → `feature-doc.md` §6 + runbook entry
  suggestion.
- Decision with multiple viable options and cross-feature impact → **propose**
  an ADR (`docs/adr/NNNN-title.md`); ask before creating it.

### D. Report

- Files documented and what was added.
- Documents created/updated (paths).
- ADRs proposed.
- Documentation you did **not** touch but suspect is stale, with reasons.
- Any `OQ`s created from bare TODOs.

## Rules

- Zero behaviour change. If you spot a bug, report it; do not fix it here.
- Do not describe *what* the code does in comments; describe *why*.
- Do not create documents the decision guide does not call for.
- Keep the six-months-later reader in mind: plain sentences, exact paths.
