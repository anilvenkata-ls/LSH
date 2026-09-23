<!--
Title format: "REQ-nnn: <imperative summary>"
Keep the "Feature folder" link — CI checks for it.
Process: docs/framework/00-overview.md
-->

## Requirement

- **Feature folder:** `docs/features/REQ-nnn-slug/`
- **Issue:** #
- **Current stage label:** `stage:plan` | `stage:implementation` | `stage:testing` | `stage:ready-to-deploy`

## Summary of change

<!-- Filled at implementation time. Ask Cursor: "@Branch (Diff with Main) write the PR Summary of change". -->

## Stage gates

### G2 — Plan approved
- [ ] `technical-plan.md` committed; `plan-reviewer` subagent run
- [ ] Reviewer (≠ author) commented "Plan approved"
- [ ] No Open Blocking `OQ`s

### G3 — Code complete
- [ ] Every plan step ticked; code matches plan (or plan change log updated and re-approved)
- [ ] Code documentation standards met (headers, doc comments, `TODO(OQ-n)` only)
- [ ] All `[ASSUMED]` markers have an `Accepted` `OQ`
- [ ] Bugbot comments resolved or answered
- [ ] `feature-doc.md` updated

### G4 — Tests green
- [ ] CI green; coverage on changed files ≥ target (`__ %`)
- [ ] `test-plan.md` complete — every AC has a Passing / Verified row
- [ ] No skipped tests without an `OQ`/issue reference

### G5 — Ready to deploy
- [ ] `release-checklist.md` complete; Missing items = 0
- [ ] Business acceptance recorded
- [ ] Release owner approved; label `stage:ready-to-deploy`

## Test evidence

<!-- How to run; coverage number; screenshots/recordings for UI. -->

## Deployment notes

<!-- Migrations and order, config/secrets needed per environment, feature flag + default, rollback steps. Or "None". -->

## Assumptions and open questions touched

<!-- OQ-n IDs raised or resolved in this PR. -->
