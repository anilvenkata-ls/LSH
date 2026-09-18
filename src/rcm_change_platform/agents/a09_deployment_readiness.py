"""Agent 9 - Deployment Readiness.

Turns the evidence gathered by the previous agents into a checklist. Items are
derived from what actually happened - a test that was generated but not executed
is not a passing test - so the verdict is auditable rather than decorative.
"""

from __future__ import annotations

from ..context import ChangeContext
from ..models import ChecklistItem, DeploymentChecklist, ImpactAction, TestStatus
from .base import Agent


class DeploymentReadinessAgent(Agent):
    name = "deployment_readiness"
    step = 9

    def execute(self, context: ChangeContext) -> str:
        checklist = DeploymentChecklist()
        self._development(context, checklist)
        self._testing(context, checklist)
        self._reporting(context, checklist)
        self._documentation(context, checklist)
        self._governance(context, checklist)

        checklist.blockers = [
            f"{item.section}: {item.item}" + (f" - {item.detail}" if item.detail else "")
            for item in checklist.items
            if item.blocking and not item.complete
        ]
        context.checklist = checklist

        complete = sum(1 for item in checklist.items if item.complete)
        verdict = "ready for deployment" if checklist.ready else f"blocked by {len(checklist.blockers)} item(s)"
        return f"{complete}/{len(checklist.items)} checklist items complete; {verdict}"

    # -- sections ---------------------------------------------------------
    def _development(self, context: ChangeContext, checklist: DeploymentChecklist) -> None:
        change_set = context.change_set
        impact = context.impact
        section = "Development"

        migration_present = bool(change_set and change_set.migration_sql.strip())
        already_present = bool(
            impact
            and change_set
            and context.repo.has_column(impact.target_fact_table, change_set.target_column)
        )
        checklist.items.append(
            ChecklistItem(
                section=section,
                item="Migration script generated",
                complete=migration_present or already_present,
                detail="column already present on the fact table" if already_present and not migration_present else "",
            )
        )

        for object_type, label in (("stored_procedure", "Stored procedure updated"), ("view", "View updated")):
            expected = [
                item.object_name
                for item in (impact.items if impact else [])
                if item.action is ImpactAction.MODIFY and item.object_type == object_type
            ]
            generated = [
                change.object_name
                for change in (change_set.object_changes if change_set else [])
                if change.object_type == object_type
            ]
            checklist.items.append(
                ChecklistItem(
                    section=section,
                    item=label,
                    complete=set(expected) == set(generated),
                    detail=", ".join(generated) if expected else "no change required",
                    blocking=bool(expected),
                )
            )

        checklist.items.append(
            ChecklistItem(
                section=section,
                item="Rollback script generated",
                complete=bool(change_set and change_set.rollback_sql.strip()),
            )
        )

    def _testing(self, context: ChangeContext, checklist: DeploymentChecklist) -> None:
        section = "Testing"
        unit, integration = context.unit_run, context.integration_run

        checklist.items.append(
            ChecklistItem(
                section=section,
                item="Unit tests generated",
                complete=bool(context.unit_suite and context.unit_suite.cases),
                detail=f"{len(context.unit_suite.cases) if context.unit_suite else 0} cases",
            )
        )
        checklist.items.append(
            ChecklistItem(
                section=section,
                item="Unit tests passed",
                complete=bool(unit and unit.executed and unit.passed),
                detail=self._test_detail(unit),
            )
        )
        checklist.items.append(
            ChecklistItem(
                section=section,
                item="Integration tests passed",
                complete=bool(integration and integration.executed and integration.passed),
                detail=self._test_detail(integration),
            )
        )
        reconciliation = context.reconciliation
        checklist.items.append(
            ChecklistItem(
                section=section,
                item="Financial reconciliation passed",
                complete=bool(reconciliation and reconciliation.executed and reconciliation.balanced),
                detail=(
                    ", ".join(line.metric for line in reconciliation.lines if not line.matched)
                    if reconciliation and not reconciliation.balanced
                    else f"{len(reconciliation.lines) if reconciliation else 0} metrics compared"
                ),
            )
        )

    def _reporting(self, context: ChangeContext, checklist: DeploymentChecklist) -> None:
        section = "Reporting"
        plan = context.power_bi
        checklist.items.append(
            ChecklistItem(
                section=section,
                item="Power BI change plan generated",
                complete=bool(plan and plan.changes),
                detail=f"{len(plan.changes) if plan else 0} actions",
            )
        )
        checklist.items.append(
            ChecklistItem(
                section=section,
                item="Semantic model refresh scheduled",
                complete=bool(plan and plan.refresh_required),
                detail=f"dataset {plan.dataset}" if plan else "",
                blocking=bool(plan and plan.refresh_required),
            )
        )
        checklist.items.append(
            ChecklistItem(
                section=section,
                item="Report visuals reviewed by a human",
                complete=False,
                detail="manual step: place the new field on the intended visuals",
                blocking=False,
            )
        )

    def _documentation(self, context: ChangeContext, checklist: DeploymentChecklist) -> None:
        section = "Documentation"
        for filename, label in (
            ("Technical_Design.md", "Technical design"),
            ("PR_Description.md", "PR description"),
            ("Release_Notes.md", "Release notes"),
        ):
            content = context.documents.get(filename, "")
            checklist.items.append(
                ChecklistItem(
                    section=section,
                    item=label,
                    complete=len(content.strip()) > 200,
                    detail=f"{len(content)} characters",
                )
            )

    def _governance(self, context: ChangeContext, checklist: DeploymentChecklist) -> None:
        section = "Governance"
        metadata = context.metadata
        column = metadata.column if metadata else None
        checklist.items.append(
            ChecklistItem(
                section=section,
                item="Column certified in the data dictionary",
                complete=bool(column and column.certified),
                detail=column.steward if column else "",
                blocking=False,
            )
        )
        checklist.items.append(
            ChecklistItem(
                section=section,
                item="PII review",
                complete=not (column and column.pii),
                detail="column is flagged as PII; obtain audience approval" if column and column.pii else "no PII involved",
                blocking=bool(column and column.pii),
            )
        )

    @staticmethod
    def _test_detail(run) -> str:
        if run is None:
            return "not generated"
        if not run.executed:
            return "generated but not executed"
        failed = [r.name for r in run.results if r.status in {TestStatus.FAILED, TestStatus.ERROR}]
        return ", ".join(failed) if failed else f"{len(run.results)} checks"
