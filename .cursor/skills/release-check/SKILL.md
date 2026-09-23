---
name: release-check
description: Stage 8 — assess deploy readiness for a feature by filling release-checklist.md from the PR, plan, test plan, and open-questions register, marking each item Done / Missing / N/A with evidence, and listing what blocks G5. Use when the user says "release check", "ready to deploy?", "are we done", or before marking a PR ready for review.
---

# /release-check — Release readiness

Process reference: `docs/framework/08-release-readiness.md`.
Template: `docs/templates/release-checklist.md`.

## Inputs

- Feature folder: `prd.md`, `technical-plan.md`, `test-plan.md`,
  `feature-doc.md`, `open-questions.md`.
- The branch diff (`@Branch (Diff with Main)`) and PR description if
  available.
- CI status if the user provides it or it is visible.

## Procedure

1. **Create or open `release-checklist.md`** from the template.
2. **Assess each row** and set **Done / Missing / N/A (reason)** with an
   evidence link or path:
   - *Scope:* every FR/AC delivered or deferred with a `REQ`; register has no
     Open items; PRD version matches; plan change log has no un-re-approved
     entries.
   - *Quality:* CI, coverage vs. target, Bugbot comments, review approval,
     security review if plan §9 flagged it, NFR measurements.
   - *Deployment / rollback:* from plan §5 and §11 — migration order,
     config/secrets per environment, flag default, compatibility, rollback
     steps and owner.
   - *Observability:* logs with feature ID, metrics/alerts, dashboard,
     first-hour health definition.
   - *Communication:* release notes line (draft one), support/ops briefing,
     business user informed.
   - *Documentation:* feature doc as-built, README/API, ADRs, runbook; grep
     for bare `TODO` and `[ASSUMED]` without an Accepted `OQ`.
   - *Business acceptance:* manual/UAT rows in `test-plan.md` verified.
3. **List the Missing items** as an actionable checklist in chat, most
   blocking first, each with the skill or action that resolves it
   (`/unit-tests`, `/document-code`, "ask release owner for rollback
   owner", …).
4. **State the G5 verdict:** Ready / Not ready, and what label and PR state
   to set.

## Rules

- Do not mark anything Done without evidence you can point at.
- Do not perform sign-offs; those are human names and dates.
- If the deployment mechanism is not documented in `CONTRIBUTING.md` →
  *Deploying*, flag that as Missing at project level.
