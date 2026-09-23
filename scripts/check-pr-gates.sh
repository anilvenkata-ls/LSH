#!/usr/bin/env bash
# PR hygiene gate for the development lifecycle framework.
# Reference: docs/framework/04-git-and-pr-workflow.md and 10-documentation.md
#
# Checks (all language-agnostic):
#   1. PR title carries a REQ-<id>              (skipped for process-only PRs)
#   2. PR body links a docs/features/REQ-... folder that exists and has intake.md + prd.md
#   3. If production code changed: technical-plan.md exists with Status Approved
#   4. If production code changed: feature-doc.md or test-plan.md in the same folder
#      changed too (override with label docs-not-needed)
#   5. Added lines contain no bare TODO/FIXME/HACK (must be TODO(OQ-n) or TODO(#n))
#   6. Added lines contain no [ASSUMED: ...] marker without an OQ-n reference
#
# Usage (CI sets these from the PR event; locally pass flags):
#   scripts/check-pr-gates.sh --title "REQ-042: add export" --body "$(cat pr.md)" --base origin/main [--labels "a,b"]
#
# A PR is "process-only" (skips checks 1–4) when its title starts with
# chore:, docs:, process:, ci: (optionally scoped, e.g. docs(framework):) or it
# carries the label no-req.

set -euo pipefail

TITLE="${PR_TITLE:-}"
BODY="${PR_BODY:-}"
LABELS="${PR_LABELS:-}"
BASE="${PR_BASE:-origin/main}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --title)  TITLE="$2";  shift 2 ;;
    --body)   BODY="$2";   shift 2 ;;
    --labels) LABELS="$2"; shift 2 ;;
    --base)   BASE="$2";   shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 64 ;;
  esac
done

failures=()
warnings=()
fail() { failures+=("$1"); }
warn() { warnings+=("$1"); }
has_label() { [[ ",${LABELS}," == *",$1,"* ]]; }

changed_files="$(git diff --name-only "${BASE}...HEAD" 2>/dev/null || git diff --name-only "${BASE}" HEAD)"

# Marker scans (checks 5–6) apply to code and feature folders only; the
# process docs and tooling legitimately talk about TODO and [ASSUMED].
marker_excludes=(
  ':(exclude)docs/framework/**' ':(exclude)docs/templates/**' ':(exclude)docs/README.md'
  ':(exclude)docs/adr/README.md' ':(exclude)docs/features/README.md'
  ':(exclude).cursor/**' ':(exclude).github/**' ':(exclude)scripts/check-pr-gates.sh'
  ':(exclude)AGENTS.md' ':(exclude)CONTRIBUTING.md' ':(exclude)README.md'
)
added_lines="$(git diff --unified=0 "${BASE}...HEAD" -- . "${marker_excludes[@]}" 2>/dev/null | grep -E '^\+[^+]' | sed 's/^+//' || true)"

# Production code = anything outside docs, process config, and markdown.
prod_changed="$(printf '%s\n' "${changed_files}" \
  | grep -Ev '^(docs/|\.github/|\.cursor/|scripts/check-pr-gates\.sh$|AGENTS\.md$|CONTRIBUTING\.md$|README\.md$)' \
  | grep -Ev '\.md$' || true)"

process_only=false
process_title_re='^(chore|docs|process|ci)(\([^)]*\))?:'
if has_label no-req || [[ "${TITLE}" =~ ${process_title_re} ]]; then
  process_only=true
fi

if [[ "${process_only}" == false ]]; then
  # 1. REQ id in title
  if [[ ! "${TITLE}" =~ REQ-[0-9]{3,} ]]; then
    fail "PR title must contain a REQ-<id> (e.g. 'REQ-042: add invoice export'). See docs/framework/04-git-and-pr-workflow.md"
  fi

  # 2. Feature folder linked and present
  folder="$(printf '%s' "${BODY}" | grep -oE 'docs/features/REQ-[0-9]{3,}-[a-z0-9-]+/?' | head -n1 | sed 's:/*$::' || true)"
  if [[ -z "${folder}" ]]; then
    fail "PR body must link the feature folder (docs/features/REQ-nnn-slug/). Use .github/PULL_REQUEST_TEMPLATE.md"
  elif [[ ! -d "${folder}" ]]; then
    fail "Feature folder '${folder}' referenced in PR body does not exist in this branch"
  else
    for f in intake.md prd.md; do
      [[ -f "${folder}/${f}" ]] || fail "Missing ${folder}/${f} — run /intake or /prd"
    done

    if [[ -n "${prod_changed}" ]]; then
      # 3. Approved plan before code
      plan="${folder}/technical-plan.md"
      if [[ ! -f "${plan}" ]]; then
        fail "Production code changed but ${plan} is missing — gate G2 not passed (docs/framework/05-technical-plan-and-review.md)"
      elif ! grep -Eiq '^\|\s*\*\*Status\*\*\s*\|\s*Approved' "${plan}"; then
        fail "${plan} Status row must read 'Approved …' (currently Draft / In review) — gate G2 not passed"
      fi

      # 4. Docs kept in step with code
      if ! has_label docs-not-needed; then
        if ! printf '%s\n' "${changed_files}" | grep -Eq "^${folder}/(feature-doc|test-plan)\.md$"; then
          fail "Production code changed but neither ${folder}/feature-doc.md nor test-plan.md was updated. Update them (/document-code, /unit-tests) or add label 'docs-not-needed' with a reason in the PR"
        fi
      fi
    fi
  fi
fi

# 5. Bare TODO / FIXME / HACK in added lines
bare_todos="$(printf '%s\n' "${added_lines}" | grep -En '\b(TODO|FIXME|HACK)\b' | grep -Ev '\b(TODO|FIXME|HACK)\((OQ-[0-9]+|#[0-9]+)\)' || true)"
if [[ -n "${bare_todos}" ]]; then
  fail "Bare TODO/FIXME/HACK found; use TODO(OQ-n) or TODO(#issue):"$'\n'"${bare_todos}"
fi

# 6. [ASSUMED] markers without an OQ reference
bare_assumed="$(printf '%s\n' "${added_lines}" | grep -En '\[ASSUMED:' | grep -Ev 'OQ-[0-9]+' || true)"
if [[ -n "${bare_assumed}" ]]; then
  fail "[ASSUMED: ...] marker without an OQ-n reference (docs/framework/03-ambiguity-handling.md):"$'\n'"${bare_assumed}"
fi

# Report
if [[ "${process_only}" == true ]]; then
  echo "ℹ Process-only PR: requirement checks 1–4 skipped."
fi
for w in "${warnings[@]:-}"; do [[ -n "$w" ]] && echo "⚠ ${w}"; done
if [[ ${#failures[@]} -gt 0 ]]; then
  echo
  echo "✖ PR gate failures (${#failures[@]}):"
  for f in "${failures[@]}"; do echo; echo "  - ${f}"; done
  exit 1
fi
echo "✔ PR gates passed."
