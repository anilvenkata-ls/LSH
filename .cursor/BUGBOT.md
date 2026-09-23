# Bugbot review guidance for this repository

This repository follows the gated lifecycle in `docs/framework/00-overview.md`.
In addition to normal bug-finding, check the items below and comment when
they are violated. Cite the framework doc in the comment so authors can
read the rule.

## Traceability

- PR title must contain a `REQ-<id>`; the PR body must link a
  `docs/features/REQ-<id>-<slug>/` folder.
- Production code changes for a feature require that folder to contain a
  `technical-plan.md` with status `Approved`. If the plan is missing or not
  approved, flag it: code was written before gate G2
  (`docs/framework/05-technical-plan-and-review.md`).
- Commit messages should start with `REQ-<id>:`.

## Ambiguity discipline (`docs/framework/03-ambiguity-handling.md`)

- Any `[ASSUMED: ...]` marker in code or docs must reference an `OQ-n` and
  that `OQ` must have status `Accepted` in `open-questions.md`. Flag
  unmatched or still-Open assumptions.
- Bare `TODO`, `FIXME`, `HACK` comments without `(OQ-n)` or `(#issue)` are
  violations.
- `TBD` in a document whose status is `Approved` is a violation.

## Code documentation (`docs/framework/10-documentation.md`)

- New public functions, classes, methods, exported types without a doc
  comment.
- New source files without a module header naming the `REQ` and linking the
  feature doc.
- Comments that narrate what the code does rather than why.
- New config keys / env vars / feature flags not documented in
  `feature-doc.md` §5.
- New third-party dependencies with no justification in `feature-doc.md` §8
  and `technical-plan.md` §3.

## Tests (`docs/framework/07-unit-testing.md`)

- Changed production code with no corresponding test changes and no
  `docs-not-needed` / `tests-not-needed` label.
- Test names that carry no `AC-` reference.
- Tests that assert implementation details (private state, call counts)
  where the AC describes observable behaviour.
- Non-deterministic constructs: real clocks, `sleep`, network calls,
  unordered-collection ordering assumptions.
- Skipped / xfail tests without an `OQ-n` or issue reference.
- Tests whose expected values appear to be copied from the implementation
  output rather than the AC.

## Documentation completeness

- Code under a feature changed but `feature-doc.md` or `test-plan.md` in the
  same folder not updated (unless labelled `docs-not-needed`).
- A migration added without rollback notes in `technical-plan.md` §5 /
  `release-checklist.md` §4.

## Security basics

- Secrets, tokens, or environment-specific URLs in code, tests, or fixtures.
- New endpoints without an authorisation check where the plan §9 specifies
  one.
- Unvalidated input at system boundaries.

## Tone

Be specific: quote the line, name the rule, link the framework doc, and
suggest the fix. Do not comment on style the formatter handles.
