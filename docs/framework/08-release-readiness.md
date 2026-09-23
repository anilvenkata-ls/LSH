# Stage 8 — Release Readiness

**Input:** PR with code, tests, and documentation complete (G3, G4 passed).
**Output:** `release-checklist.md` complete; PR approved and labelled
`stage:ready-to-deploy` (G5). The change is ready for whatever deployment
mechanism the project uses.
**Owner:** Release owner confirms; developer prepares.
**Cursor:** `/release-check` fills the checklist from the PR, plan, and test
plan, and lists what is still missing.

## Purpose

"Done" in this framework means *deployable*, not *merged*. This stage makes
sure the operational half of the change — rollout, rollback, monitoring,
communication — has been thought about with the same care as the code.

## Steps

1. **Run `/release-check`.** The skill reads the feature folder and the PR
   and drafts `release-checklist.md` from
   `docs/templates/release-checklist.md`, marking each item Done / Missing /
   N/A with evidence links.
2. **Complete the Missing items.** Typical gaps: rollback steps for a
   migration, a missing feature-flag default, no dashboard/alert for a new
   failure mode, no note to support.
3. **Business acceptance.** The business user (or their delegate) verifies
   the manual/UAT rows in `test-plan.md` on a staging environment and
   records acceptance in the checklist by name and date.
4. **Final review.** Mark the PR *Ready for review*. The release owner reviews
   the checklist and deployment notes and approves.
5. **Pass G5.** Label `stage:ready-to-deploy`. Merge (squash) when the
   deployment window allows.

## Checklist areas

The template groups items under:

- **Scope confirmation** — every FR/AC delivered or explicitly deferred with
  a new `REQ`; no Open `OQ`s of any severity; PRD version matches what was
  built.
- **Quality** — CI green; coverage threshold; Bugbot comments resolved;
  security review if the plan flagged it; performance NFRs measured.
- **Deployment** — migration order and idempotency; config/secrets provided
  in each environment; feature flag name and default; backward compatibility
  with the previous version during rollout.
- **Rollback** — exact steps; data rollback if a migration is involved; who
  executes it; how long it takes.
- **Observability** — logs, metrics, alerts for the new failure paths;
  dashboard link; what "healthy" looks like in the first hour.
- **Communication** — release notes line; support/ops briefed; business user
  informed of go-live date; any customer-facing notice.
- **Documentation** — `feature-doc.md` current; README/API docs updated;
  ADRs recorded; runbook entry if operational behaviour changed.
- **Sign-offs** — developer, reviewer, business acceptance, release owner.

## Deployment mechanics

This framework stops at "ready to deploy" on purpose: deployment tooling
varies by project. Record the project's actual mechanism (CD pipeline,
manual release, scheduled window) in `CONTRIBUTING.md` under *Deploying*,
and link it from the checklist's *Deployment* section.

## After deployment

- Confirm the success measure from `intake.md` is being tracked; note where.
- Close the GitHub issue with a comment linking the PR and the release.
- If anything in the checklist turned out to be wrong in production, add a
  short *Lessons* section to `feature-doc.md` and, if it is a process gap,
  propose a change to the framework docs via a normal PR.
