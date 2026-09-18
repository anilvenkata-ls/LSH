"""Markdown renderers for the change package.

The renderers are pure functions of the :class:`ChangeContext`, so the
documentation agent can produce them mid-pipeline and the packaging agent can
re-render them once test evidence exists without either duplicating logic.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .context import ChangeContext
from .models import ImpactAction, TestRun, TestStatus


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _bullets(values, empty: str = "_None_") -> str:
    values = [v for v in values if v]
    if not values:
        return empty
    return "\n".join(f"- {value}" for value in values)


def _table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_No rows._"
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def _test_summary(run: TestRun | None) -> str:
    if run is None:
        return "not generated"
    if not run.executed:
        return f"{len(run.results)} cases generated, not executed"
    return (
        f"{run.count(TestStatus.PASSED)} passed, {run.count(TestStatus.FAILED)} failed, "
        f"{run.count(TestStatus.ERROR)} errored of {len(run.results)}"
    )


def _test_table(run: TestRun | None) -> str:
    if run is None:
        return "_No tests generated._"
    return _table(
        ["Test", "Category", "Status", "Expectation", "Observed"],
        [
            [result.name, result.category, result.status.value, result.expectation, result.actual or "-"]
            for result in run.results
        ],
    )


# ---------------------------------------------------------------------------
# Requirement
# ---------------------------------------------------------------------------


def requirement(context: ChangeContext) -> str:
    request = context.request
    metadata = context.metadata
    if request is None:
        return "# Requirement\n\nThe request could not be parsed.\n"

    lines = [
        f"# Requirement {request.request_id}",
        "",
        f"_Generated {_timestamp()} by the RCM change automation platform._",
        "",
        "## Business Request",
        "",
        f"> {request.raw_request}",
        "",
        "## Structured Requirement",
        "",
        "```json",
        _json_block(
            {
                "report": request.report,
                "requested_column": request.requested_column,
                "business_reason": request.business_reason or "not supplied",
            }
        ),
        "```",
        "",
        _table(
            ["Attribute", "Value"],
            [
                ["Request ID", request.request_id],
                ["Requested by", request.requested_by],
                ["Change type", request.change_type.value],
                ["Parser", request.parser],
                ["Match confidence", f"{request.confidence:.2f}"],
            ],
        ),
    ]

    if metadata and metadata.column:
        column = metadata.column
        lines += [
            "",
            "## Resolved Source",
            "",
            _table(
                ["Attribute", "Value"],
                [
                    ["Business term", column.business_term],
                    ["Source table", column.physical_table],
                    ["Source column", column.physical_column],
                    ["Data type", column.data_type],
                    ["Nullable", str(column.nullable)],
                    ["Certified", str(column.certified)],
                    ["Steward", column.steward or "unassigned"],
                    ["Domain values", ", ".join(column.domain_values) or "not constrained"],
                ],
            ),
            "",
            f"**Definition.** {column.definition}",
            "",
            "## Metadata Evidence",
            "",
            _table(
                ["Source", "Reference", "Detail"],
                [[e.source, e.reference, e.detail] for e in metadata.evidence],
            ),
        ]
        if metadata.related_tickets:
            lines += [
                "",
                "## Related Jira History",
                "",
                _bullets(f"{t['key']}: {t['summary']} ({t['status']})" for t in metadata.related_tickets),
            ]

    if request.clarifications:
        lines += ["", "## Clarifications Needed", "", _bullets(request.clarifications)]
    return "\n".join(lines) + "\n"


def _json_block(payload: dict) -> str:
    import json

    return json.dumps(payload, indent=2)


# ---------------------------------------------------------------------------
# Technical design
# ---------------------------------------------------------------------------


def technical_design(context: ChangeContext) -> str:
    request, metadata, impact = context.request, context.metadata, context.impact
    if request is None or impact is None or metadata is None or metadata.column is None:
        return "# Technical Design\n\nThe pipeline halted before a design could be produced.\n"

    column = metadata.column
    change_set = context.change_set
    lines = [
        f"# Technical Design - {request.request_id}",
        "",
        f"**Change:** add `{column.physical_column}` to **{request.report}**",
        f"**Generated:** {_timestamp()}",
        "",
        "## 1. Business Request",
        "",
        f"> {request.raw_request}",
        "",
        f"**Business reason.** {request.business_reason or 'Not supplied by the requester.'}",
        "",
        "## 2. Source Data",
        "",
        _table(
            ["Attribute", "Value"],
            [
                ["Source table", column.physical_table],
                ["Source column", column.physical_column],
                ["Data type", column.data_type],
                ["Definition", column.definition],
                ["Steward", column.steward or "unassigned"],
                ["Upstream producers", ", ".join(metadata.upstream_dependencies) or "none recorded"],
            ],
        ),
        "",
        "## 3. Data Flow",
        "",
        "```",
        "\n   |\n   v\n".join(impact.propagation_path),
        "```",
        "",
        f"**Join strategy.** {impact.join_plan.get('detail', 'n/a')}",
        "",
        "## 4. Impacted Objects",
        "",
        _table(
            ["Object", "Type", "Impact", "Layer", "Risk", "Rationale"],
            [
                [item.object_name, item.object_type, item.action.value, item.layer, item.risk, item.rationale]
                for item in impact.items
            ],
        ),
        "",
        "## 5. ETL Changes",
        "",
    ]

    if change_set:
        lines.append(_bullets([f"`{c.object_name}` ({c.object_type}): {c.summary}" for c in change_set.object_changes]))
        if change_set.migration_sql:
            lines += ["", "### Migration", "", "```sql", change_set.migration_sql.strip(), "```"]
        for change in change_set.object_changes:
            lines += [
                "",
                f"### Diff - {change.object_name}",
                "",
                "```diff",
                change.diff.strip() or "(no textual change)",
                "```",
            ]
    else:
        lines.append("_No SQL changes were generated._")

    power_bi = context.power_bi
    lines += ["", "## 6. Reporting Changes", ""]
    if power_bi:
        lines.append(
            _table(
                ["Target", "Type", "Action", "Detail"],
                [[c.target, c.target_type, c.action, c.detail] for c in power_bi.changes],
            )
        )
        if power_bi.tmdl_snippet:
            lines += ["", "### Semantic model definition", "", "```tmdl", power_bi.tmdl_snippet.strip(), "```"]
    else:
        lines.append("_No Power BI plan was generated._")

    lines += [
        "",
        "## 7. Testing",
        "",
        f"- Unit tests: {_test_summary(context.unit_run)}",
        f"- Integration tests: {_test_summary(context.integration_run)}",
        f"- Financial reconciliation: {_reconciliation_verdict(context)}",
        "",
        "## 8. Risks",
        "",
        _bullets(_risks(context)),
        "",
        "## 9. Rollback Strategy",
        "",
        _bullets(
            [
                "Execute `Rollback_Script.sql`, which restores the previous procedure and view definitions and drops the new column.",
                f"Re-run the loading procedure to rebuild {impact.target_fact_table} with the original definition.",
                "Refresh the Power BI dataset so the semantic model returns to the previous schema.",
            ]
        ),
        "",
    ]
    return "\n".join(lines)


def _reconciliation_verdict(context: ChangeContext) -> str:
    report = context.reconciliation
    if report is None:
        return "not run"
    if not report.executed:
        return "not executed"
    if report.balanced:
        return f"balanced across {len(report.lines)} metrics"
    drifted = ", ".join(line.metric for line in report.lines if not line.matched)
    return f"OUT OF BALANCE: {drifted}"


def _risks(context: ChangeContext) -> list[str]:
    risks: list[str] = []
    impact = context.impact
    metadata = context.metadata
    if impact:
        if impact.join_plan.get("strategy") == "new_join":
            risks.append(
                "A new LEFT JOIN is introduced into the fact load; unmatched rows will carry a NULL attribute "
                "and row counts must be confirmed unchanged."
            )
        for item in impact.items:
            if item.action is ImpactAction.REFRESH:
                risks.append(f"`{item.object_name}` must be refreshed before the report reflects the change.")
        risks.extend(impact.warnings)
    if metadata and metadata.column:
        if metadata.column.pii:
            risks.append(f"`{metadata.column.physical_column}` is flagged as PII; confirm the report audience.")
        if not metadata.column.certified:
            risks.append(f"`{metadata.column.physical_column}` is not certified in the data dictionary.")
    risks.extend(context.warnings)
    deduped: list[str] = []
    for risk in risks:
        if risk not in deduped:
            deduped.append(risk)
    return deduped or ["No material risks identified by the automated analysis."]


# ---------------------------------------------------------------------------
# Pull request description
# ---------------------------------------------------------------------------


def pr_description(context: ChangeContext) -> str:
    request, impact = context.request, context.impact
    if request is None or impact is None:
        return "# Pull Request\n\nThe pipeline halted before a change was produced.\n"

    column = context.metadata.column.physical_column if context.metadata and context.metadata.column else ""
    modified = [item.object_name for item in impact.items if item.action is ImpactAction.MODIFY]
    refreshed = [item.object_name for item in impact.items if item.action is ImpactAction.REFRESH]
    reviewed = [item.object_name for item in impact.items if item.action is ImpactAction.REVIEW]

    lines = [
        f"## Summary",
        "",
        f"Added `{column}` to the **{request.report}** ({request.request_id}).",
        "",
        f"{request.business_reason or 'Requested by the business for reporting analysis.'}",
        "",
        "## Impacted Objects",
        "",
        "**Modified**",
        "",
        _bullets(modified),
        "",
        "**Refresh required**",
        "",
        _bullets(refreshed),
        "",
        "**Reviewed, no change**",
        "",
        _bullets(reviewed),
        "",
        "## Testing",
        "",
        f"- Unit tests: {_test_summary(context.unit_run)}",
        f"- Integration tests: {_test_summary(context.integration_run)}",
        f"- Financial reconciliation: {_reconciliation_verdict(context)}",
        "",
        "## Deployment",
        "",
        _bullets(_deployment_bullets(context)),
        "",
        "## Rollback",
        "",
        "`Rollback_Script.sql` restores the previous definitions and drops the added column.",
        "",
        "## Reviewer Checklist",
        "",
        _bullets(
            [
                "Confirm the business definition of the new column with the data steward.",
                "Confirm the generated diffs match the team's SQL standards.",
                "Confirm the Power BI field is placed on the intended visuals.",
            ]
        ),
        "",
        "_Generated by the RCM change automation platform; review before merge._",
        "",
    ]
    return "\n".join(lines)


def _deployment_bullets(context: ChangeContext) -> list[str]:
    checklist = context.checklist
    if checklist is None:
        return ["Deployment readiness has not been evaluated."]
    verdict = "READY" if checklist.ready else "BLOCKED"
    bullets = [f"Deployment readiness: **{verdict}**"]
    bullets += [f"{item.marker} {item.section}: {item.item}" for item in checklist.items]
    return bullets


# ---------------------------------------------------------------------------
# Release notes and validation report
# ---------------------------------------------------------------------------


def release_notes(context: ChangeContext) -> str:
    request, impact = context.request, context.impact
    if request is None or impact is None:
        return "# Release Notes\n\nNo change was produced.\n"
    column = context.metadata.column if context.metadata else None
    release = context.options.release or request.request_id
    lines = [
        f"# Release Notes - {release}",
        "",
        f"**Date:** {_timestamp()}",
        f"**Request:** {request.request_id} - {request.raw_request}",
        "",
        "## What changed",
        "",
        _bullets(
            [
                f"`{column.physical_column}` ({column.data_type}) is now available on **{request.report}**."
                if column
                else "Column added to the report.",
                f"Sourced from `{column.physical_table}` and denormalised onto `{impact.target_fact_table}`."
                if column
                else "",
            ]
        ),
        "",
        "## Deployment steps",
        "",
        _bullets(
            [
                "Run `Generated_SQL.sql` in the target environment.",
                f"Re-run the loading procedure for `{impact.target_fact_table}` (a full snapshot reload backfills history).",
                f"Refresh the Power BI dataset `{context.power_bi.dataset if context.power_bi else ''}`.",
                "Publish the updated report and validate the new field on the impacted visuals.",
            ]
        ),
        "",
        "## Validation performed",
        "",
        _bullets(
            [
                f"Unit tests: {_test_summary(context.unit_run)}",
                f"Integration tests: {_test_summary(context.integration_run)}",
                f"Financial reconciliation: {_reconciliation_verdict(context)}",
            ]
        ),
        "",
        "## Known impacts",
        "",
        _bullets(_risks(context)),
        "",
    ]
    return "\n".join(lines)


def validation_report(context: ChangeContext) -> str:
    request = context.request
    header = request.request_id if request else "unparsed request"
    lines = [
        f"# Validation Report - {header}",
        "",
        f"**Generated:** {_timestamp()}",
        f"**Execution mode:** {'sandbox executed' if context.options.execute_tests else 'generation only'}",
        "",
        "## Financial Reconciliation",
        "",
    ]
    report = context.reconciliation
    if report and report.lines:
        lines.append(
            _table(
                ["Metric", "Before", "After", "Delta", "Result"],
                [
                    [
                        line.metric,
                        f"{line.before:,.2f}",
                        f"{line.after:,.2f}",
                        f"{line.difference:,.2f}",
                        "PASS" if line.matched else "FAIL",
                    ]
                    for line in report.lines
                ],
            )
        )
    else:
        lines.append("_Reconciliation was not executed._")

    lines += ["", "## Unit Tests", "", _test_table(context.unit_run)]
    lines += ["", "## Integration Tests", "", _test_table(context.integration_run)]

    checklist = context.checklist
    lines += ["", "## Deployment Readiness", ""]
    if checklist:
        lines.append(
            _table(
                ["Section", "Item", "Status", "Detail"],
                [
                    [item.section, item.item, "complete" if item.complete else "outstanding", item.detail]
                    for item in checklist.items
                ],
            )
        )
        lines += ["", f"**Verdict:** {'READY FOR DEPLOYMENT' if checklist.ready else 'BLOCKED'}"]
        if checklist.blockers:
            lines += ["", "**Blockers**", "", _bullets(checklist.blockers)]
    else:
        lines.append("_Readiness was not evaluated._")

    lines += [
        "",
        "## Agent Run Log",
        "",
        _table(
            ["Step", "Agent", "Status", "Duration (ms)", "Summary"],
            [[r.step, r.agent, r.status, f"{r.duration_ms:.1f}", r.summary] for r in context.reports],
        ),
        "",
    ]
    return "\n".join(lines)
