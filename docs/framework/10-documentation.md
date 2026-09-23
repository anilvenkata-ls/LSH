# Documentation — What, When, and How

The framework treats documentation as a stage output, not a chore at the
end. This page is the single reference for **which documents exist, when
each is created, who owns it, and how Cursor generates it on demand**.

## Document catalogue

| Document | Created at | Owner | Template | Purpose | Lives |
|----------|-----------|-------|----------|---------|-------|
| `intake.md` | Stage 1 | Product owner | `docs/templates/requirement-intake.md` | Business request in business terms | Feature folder |
| `open-questions.md` | Stage 2 (updated all stages) | Product owner | `docs/templates/open-questions.md` | Ambiguity register | Feature folder |
| `prd.md` | Stage 2 | Product owner; business sign-off | `docs/templates/prd.md` | The requirement contract | Feature folder |
| `technical-plan.md` | Stage 4 | Developer | `docs/templates/technical-plan.md` | Reviewed design and step list | Feature folder |
| `test-plan.md` | Stage 6 | Developer | `docs/templates/test-plan.md` | AC → test traceability | Feature folder |
| `feature-doc.md` | Stage 5–7 | Developer | `docs/templates/feature-doc.md` | How the feature works, how to run/operate it, decisions | Feature folder |
| `release-checklist.md` | Stage 8 | Developer; release owner signs | `docs/templates/release-checklist.md` | Deploy readiness | Feature folder |
| ADR (`docs/adr/NNNN-title.md`) | Whenever an architectural decision is made | Developer | `docs/templates/adr.md` | Record a decision that outlives one feature | `docs/adr/` |
| Code documentation | Stage 5 | Developer | Standards in `.cursor/rules/code-documentation.mdc` | Docstrings, module headers, why-comments | In source |
| Module / package README | When a new top-level module is added | Developer | Section list in `feature-doc.md` template | Entry point for a code area | Next to the code |
| API reference | When public interfaces change | Developer | Generated from code where the stack allows | Consumer-facing contract | `docs/api/` or generated site |
| Runbook entry | When operational behaviour changes | Developer + ops | Section in `feature-doc.md` → copied to runbook | On-call guidance | Project runbook |
| PR description | Stage 3 onward | Developer | `.github/PULL_REQUEST_TEMPLATE.md` | Review dashboard | GitHub |

## "Create a document when needed" — decision guide

| Situation | Create / update |
|-----------|-----------------|
| New requirement arrives | Feature folder with `intake.md` |
| Anyone has to guess what a requirement means | `open-questions.md` entry |
| A design choice has more than one reasonable option and affects more than this feature | ADR |
| A new module, service, package, or top-level directory | Module README (or a section in `feature-doc.md` for small ones) |
| A new config key, env var, or feature flag | `feature-doc.md` *Configuration* section + a comment where it is read |
| A new API endpoint / event / CLI flag | API reference + `feature-doc.md` *Interfaces* |
| A new failure mode that ops may see | `feature-doc.md` *Operations* + runbook entry |
| A dependency added | One sentence in `feature-doc.md` *Dependencies* explaining why |
| A hack, workaround, or known limitation | `feature-doc.md` *Known limitations* + a why-comment at the site |
| Something surprised you in production | `feature-doc.md` *Lessons* |

If none of these apply, do not create a document. Documentation that
nobody needs is a maintenance cost.

## The feature document (`feature-doc.md`)

This is the answer to "how does this thing work?" six months later. It is
written **during** implementation (start it at plan approval, fill it as
steps land) and finished before G5. Sections, per the template:

1. Summary — two sentences; link to PRD and plan.
2. How it works — the design as built (not as planned, if they differ), with
   a diagram if there are more than three moving parts.
3. Interfaces — endpoints, events, CLI, UI entry points.
4. Data — tables/fields touched, migrations, retention.
5. Configuration — every key/flag, default, and effect.
6. Operations — how to tell it is healthy, logs to look for, alerts, common
   failures and what to do.
7. Testing — how to run the tests; where fixtures come from.
8. Dependencies — new libraries or services and why.
9. Decisions — short list; link ADRs.
10. Known limitations and deferred scope (with `REQ` IDs for the deferred
    parts).
11. Change log.

## Code-level documentation standards

Enforced by `.cursor/rules/code-documentation.mdc` and checked by Bugbot:

- **File/module header** — purpose, originating `REQ`, link to feature doc.
- **Public API docstrings** — purpose, parameters, return, errors, notable
  behaviour. Use the language's idiom (docstring, JSDoc, GoDoc, etc.).
- **Why-comments** for anything non-obvious: workarounds, business rules,
  ordering constraints, performance choices. Reference `OQ-n`, ADR, or
  ticket where applicable.
- **No narrating comments** (`// loop over items`).
- **`TODO`/`FIXME`** must carry an `OQ-n` or issue reference.
- **Examples** in docstrings for anything with a non-trivial calling
  convention.

## Generating documentation with Cursor

`/document-code` is the single entry point. It:

1. Looks at the current selection, open file, or `@Branch (Diff with Main)`.
2. Adds or repairs module headers and public docstrings to the standard,
   without changing behaviour.
3. Creates `feature-doc.md` from the template if missing, or updates the
   sections affected by the diff.
4. Proposes an ADR if it detects a decision worth recording (multiple
   viable options, cross-feature impact) and asks before creating it.
5. Lists documentation it did **not** update but thinks may be stale.

The `doc-writer` subagent does the same for larger scopes ("document the
whole `billing/` module"). In CI or from a terminal, the same skill runs
headless via the Cursor CLI (`agent -p "/document-code …"`).

## Keeping docs honest

- The `pr-gates` CI job fails a PR that changes code under a feature's
  scope without touching `feature-doc.md` or `test-plan.md` in the same
  feature folder (override with the `docs-not-needed` label and a reason in
  the PR).
- Bugbot flags public functions without docstrings and bare `TODO`s.
- The release checklist has a *Documentation* section that the release
  owner signs.
- Approved documents never contain `TBD`; they contain `OQ-n` references.
