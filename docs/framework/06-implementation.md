# Stage 5 — Implementation

**Input:** approved technical plan (G2 passed).
**Output:** code implementing each plan step, committed in reviewable units,
documented as it is written.
**Owner:** Developer (author).
**Cursor:** `/implement` — works through the plan one step at a time; rules
in `.cursor/rules/` enforce documentation and testing standards.

## Working loop

For each step in `technical-plan.md`:

```
 /implement step N ─▶ review the diff ─▶ adjust ─▶ run tests ─▶ commit "REQ-042: step N — <summary>"
```

1. **Tell the agent which step.** `/implement` reads the plan, picks the next
   unchecked step (or the one you name), and proposes the change. It does not
   go beyond that step unless you ask.
2. **Review before accepting.** Read the diff the way a reviewer would. The
   `workflow` rule instructs the agent to explain *why* for anything not
   obvious from the plan. If the agent had to make a decision the plan did
   not cover, it must add an `[ASSUMED: …]` marker and an `OQ` entry — check
   that it did.
3. **Run the existing tests** before committing. New tests for the step are
   written in the same step where practical (see
   [07-unit-testing.md](07-unit-testing.md)); at minimum, nothing already
   green may go red.
4. **Commit per step** with the `REQ-<id>: …` format. Tick the step in the
   plan's checklist so the next `/implement` call knows where to resume.
5. **Push regularly.** Bugbot reviews each push; deal with its comments while
   the context is fresh rather than in a batch at the end.

## Code standards that apply

These are enforced through `.cursor/rules/` while the agent writes code, and
through Bugbot at PR time. They apply to human-written code equally.

### Documentation in code

- Every public module/file starts with a header comment: what it is for,
  which `REQ` introduced it, and pointers to the feature doc.
- Every public function, class, and method has a docstring/doc comment:
  purpose, parameters, return value, errors raised, and any non-obvious
  behaviour. Private helpers need one only if their name does not say it all.
- Comments explain **why**, not what. `// increment counter` is noise;
  `// ledger API rejects batches > 500 rows (OQ-7)` is documentation.
- `TODO` comments must reference an `OQ-n` or an issue number. Bare `TODO`s
  are flagged by Bugbot and the `pr-gates` job.
- Configuration keys, environment variables, and feature flags are documented
  where they are read *and* in `feature-doc.md`.

### Structure

- Follow the plan's module boundaries. If the plan is wrong, change the plan
  first (see re-planning in
  [05-technical-plan-and-review.md](05-technical-plan-and-review.md)).
- Prefer small, pure functions; side effects at the edges. This is what makes
  unit testing cheap in the next stage.
- No new dependency without a line in the plan's *Affected areas* and a
  sentence in the feature doc explaining why.
- Input validation at system boundaries; authorisation checks where the plan
  says they go.
- No secrets, tokens, or environment-specific URLs in code or tests.

### Error handling and logging

- Fail loudly on programmer errors; fail gracefully on user or external
  errors, with a message the PRD's failure-path ACs describe.
- Log at boundaries with the `REQ` ID or feature name so production issues
  can be traced back to the requirement.

## Using Cursor well at this stage

- **Give it the plan, not the PRD.** The plan is the developer-approved
  interpretation. `/implement` attaches it automatically; if you prompt
  manually, use `@docs/features/REQ-042-…/technical-plan.md`.
- **One step per conversation turn.** Large multi-step prompts produce
  diffs that are hard to review and defeat the purpose of G2.
- **Ask for the explanation, then the code.** "Explain how you will implement
  step 3, then implement it" catches misunderstandings before code appears.
- **Use `@Branch (Diff with Main)`** to ask "does the current diff cover
  every AC in the plan's traceability table? List gaps." before requesting
  code review.
- **Let the rules work.** If the agent produces undocumented functions, the
  `code-documentation` rule is not attached — check its `globs` cover your
  source directory.

## Exit criteria (leading into G3)

- Every plan step ticked and committed.
- All `[ASSUMED]` markers in code have an *Accepted* `OQ`.
- Existing tests pass locally and in CI.
- PR *Summary of change* section written (ask the agent from the branch
  diff).
- Code documentation present per the standards above.
- Label moved to `stage:testing`.
