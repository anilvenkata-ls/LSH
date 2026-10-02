# Document an RCM job

Generate or refresh the reference page for one of the ten pipeline jobs, in the
house shape, with every fact verified against the code.

Usage: `/document-rcm-job <job number, job name, or "all">`

## 1. Fix the scope

Resolve the argument to one or more jobs via the table in
[`docs/jobs/README.md`](../../docs/jobs/README.md). With no argument, use the
job whose file is open or most recently changed. State the scope before
starting.

## 2. Read before writing

For each job in scope, read in this order:

1. `src/rcm_change_platform/agents/a<nn>_*.py` — the whole file, not a search.
2. `src/rcm_change_platform/context.py` and `models.py` for the artifact types
   the job reads and writes.
3. Any supporting module the job leans on: `sqlkit.py` for job 4,
   `catalog/lineage.py` for job 3, `sandbox/` for jobs 6 and 7,
   `rendering.py` for jobs 5 and 10.
4. The job's tests, found by searching `tests/` for its class name.

Do not write the page from the existing documentation. The point of
regenerating is to catch where the code has moved on.

## 3. Write the page

`docs/jobs/<nn>-<kebab-name>.md`, with this header line and these seven
sections, in this order:

```
# Job <n> — <Title>

`<ClassName>` · `src/rcm_change_platform/agents/<file>.py` · step <n>
```

1. **Purpose** — two or three sentences: what it is responsible for and the
   judgement behind its position in the pipeline.
2. **Contract** — a Reads table (source → what it is used for) and a Writes
   table (context field → contents). This is the most important section.
3. **How it works** — the algorithm as numbered steps, naming the real
   decisions and why they were made that way.
4. **Halt conditions** — a table of every path: condition, the message the user
   sees verbatim, and what they should do about it. Find them by searching the
   job for `context.halt(` and `raise`.
5. **Warnings** — every `context.warn(` call, when it fires and what it causes
   downstream.
6. **Key functions** — a table of the methods worth knowing, by name, with one
   line each. Include the supporting-module functions the job depends on.
7. **Tests and extension points** — which test files cover it, then the things
   to be careful about when changing it, as bolded leads with an explanation.

## 4. Verify every fact

Nothing goes in the page that you have not confirmed:

```bash
python -m pytest
rcm-change run "Add Patient Financial Class to the AR Aging Report" -o /tmp/rcm
```

- Counts, totals and object names: check
  `/tmp/rcm/Change_Request/Run_Manifest.json`.
- Quoted messages, SQL and generated snippets: copy them from the code or the
  produced artifact, do not retype from memory.
- Thresholds and constants: cite the value, and say what it means rather than
  only what it is.

Prefer file paths and symbol names over line numbers, which go stale.

## 5. Update the surroundings

- Add or correct the job's row in `docs/jobs/README.md` and in the `AGENTS.md`
  job table.
- If the contract changed, update
  [`docs/jobs/pipeline-contracts.md`](../../docs/jobs/pipeline-contracts.md).
- If a halt condition was added or removed, update the consolidated halt table
  in `docs/jobs/README.md`.

## 6. Report

List the pages written, the facts you verified by running something, and
anything the code does that the documentation previously got wrong — that last
one is the useful output of a refresh.

## Rules

- Zero code changes. If you find a bug, report it; do not fix it here.
- Describe *why*, not *what*. A reader can see what the code does; the page
  exists to explain the reasoning they cannot see.
- Write for someone reading this in six months with no context: plain
  sentences, exact paths, no shorthand invented on the spot.
- Do not document aspiration. If something is a limitation, say so plainly in
  the extension points.
