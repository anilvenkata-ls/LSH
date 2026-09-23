# Agent instructions for this repository

This repository runs a gated development lifecycle:
**intake → PRD → git/PR → technical plan (developer-reviewed) → implementation → unit tests → documentation → release readiness.**
Read `docs/framework/00-overview.md` for the full picture. The rules below
apply to every agent (desktop, Cloud Agent, CLI) working here.

## Where things live

- One folder per requirement: `docs/features/REQ-<id>-<slug>/` containing
  `intake.md`, `open-questions.md`, `prd.md`, `technical-plan.md`,
  `test-plan.md`, `feature-doc.md`, `release-checklist.md`.
- Templates: `docs/templates/`. Always start a new artifact from its template.
- Architecture decisions: `docs/adr/NNNN-title.md` (template `docs/templates/adr.md`).
- Process docs: `docs/framework/`.
- Stage skills: `/intake`, `/prd`, `/clarify`, `/tech-plan`, `/implement`,
  `/unit-tests`, `/document-code`, `/release-check`.

## Non-negotiables

1. **Respect the gates.** Do not write production code for a requirement
   whose `technical-plan.md` is not marked `Approved`. Do not write a
   technical plan for a PRD that is not `Approved`. If asked to skip ahead,
   say which gate is unmet and offer to run the skill for the missing stage.
2. **Never guess silently.** When you have to interpret something the
   PRD/plan does not specify, write `[ASSUMED: <what you assumed>]` at the
   point of use *and* add an entry to the feature's `open-questions.md`
   (type Assumption, with options and a recommendation). Ask the user to
   confirm before relying on it for tests.
3. **Trace everything to IDs.** Use `REQ-`, `FR-`, `AC-`, `NFR-`, `OQ-` IDs in
   plans, code comments, test names, commit messages, and PR text.
4. **Document as you code.** Public modules get a header (purpose, REQ,
   link to feature doc); public functions/classes get doc comments; comments
   explain *why*, never narrate *what*. `TODO`s must reference `OQ-n` or an
   issue.
5. **Tests derive from acceptance criteria**, not from the implementation.
   Name tests with the AC ID. Cover unhappy paths. No non-determinism.
6. **Small steps, small commits.** Implement one plan step at a time.
   Commit message format: `REQ-<id>: <imperative summary>` with FR/AC/OQ
   references in the body.
7. **No secrets in the repo.** Ever. Config keys are documented in
   `feature-doc.md` §5.

## When asked to create a document

Consult the decision guide in `docs/framework/10-documentation.md`. Create
only what the situation calls for, from the template, in the right location.
If a document already exists, update the affected sections and its change
log instead of creating a new one.

## Cursor Cloud specific instructions

- Branch names you create should carry the `REQ-` ID in the PR title even if
  the branch is `cursor/…`.
- Open PRs as drafts using `.github/PULL_REQUEST_TEMPLATE.md`; fill the
  *Feature folder* link and the stage checklist.
- Commit in logical units (docs / plan / step n / tests / docs update).
- Project toolchain is not yet fixed. If tests exist, discover the runner
  from `package.json`, `pyproject.toml`, `go.mod`, or similar before running.
