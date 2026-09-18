"""Agent 8 - Power BI Impact.

Maps the warehouse change onto the semantic model: which dataset table gains the
column, which measures and relationships sit on that table, which visuals should
surface it, and the TMDL definition to apply. Nothing is published; the output
is a reviewable plan plus the refresh requirement.
"""

from __future__ import annotations

from ..context import ChangeContext
from ..models import ImpactAction, PowerBIChange, PowerBIPlan
from .base import Agent

_DAX_TYPES = {
    "VARCHAR": "string",
    "CHAR": "string",
    "TEXT": "string",
    "NUMERIC": "decimal",
    "DECIMAL": "decimal",
    "INTEGER": "int64",
    "INT": "int64",
    "BIGINT": "int64",
    "DATE": "dateTime",
    "TIMESTAMP": "dateTime",
    "BOOLEAN": "boolean",
}


class PowerBIImpactAgent(Agent):
    name = "power_bi_impact"
    step = 8

    def execute(self, context: ChangeContext) -> str:
        request, metadata, impact = context.request, context.metadata, context.impact
        if request is None or metadata is None or metadata.column is None or impact is None:
            context.halt(self.name, "Power BI analysis requires the metadata document and impact matrix.")
            return "missing prerequisites"

        report = context.repo.report(request.report)
        if report is None:
            context.halt(self.name, f"Report '{request.report}' is not in the Power BI metadata.")
            return "report not found"

        dataset_name = report.get("dataset", "")
        dataset = context.repo.dataset(dataset_name) or {}
        column = metadata.column.physical_column
        friendly = metadata.column.business_term or column.replace("_", " ").title()

        plan = PowerBIPlan(
            dataset=dataset_name,
            report=request.report,
            workspace=dataset.get("workspace", report.get("workspace", "")),
            refresh_required=dataset.get("storage_mode", "Import").lower() == "import",
        )

        modified_views = {
            item.object_name
            for item in impact.items
            if item.action is ImpactAction.MODIFY and context.repo.view(item.object_name)
        }
        target_tables = [table for table in dataset.get("tables", []) if table.get("source") in modified_views]

        if not target_tables:
            context.warn(
                f"No table in dataset '{dataset_name}' sources from a modified view; "
                "the dataset may need a manual query change."
            )

        for table in target_tables:
            plan.changes.append(
                PowerBIChange(
                    target=f"{dataset_name}.{table['name']}",
                    target_type="dataset_table",
                    action="Add column",
                    detail=f"Add '{column}' from {table['source']} to table '{table['name']}'.",
                )
            )
            plan.tmdl_snippet = self._tmdl(table["name"], column, friendly, metadata.column.data_type)

            measures = [m["name"] for m in dataset.get("measures", []) if m.get("table") == table["name"]]
            plan.impacted_measures.extend(measures)
            relationships = [
                f"{rel['from']} -> {rel['to']}"
                for rel in dataset.get("relationships", [])
                if table["name"] in rel.get("from", "") or table["name"] in rel.get("to", "")
            ]
            plan.impacted_relationships.extend(relationships)

            for page in report.get("pages", []):
                for visual in page.get("visuals", []):
                    if self._visual_uses_table(visual, table, measures):
                        plan.impacted_visuals.append(f"{page['name']} / {visual['id']} ({visual['type']})")

        if plan.refresh_required:
            plan.changes.append(
                PowerBIChange(
                    target=dataset_name,
                    target_type="dataset",
                    action="Refresh semantic model",
                    detail=f"Import model on schedule '{dataset.get('refresh_schedule', 'unscheduled')}' "
                    "must be refreshed before the column appears.",
                )
            )
        for measure in dict.fromkeys(plan.impacted_measures):
            plan.changes.append(
                PowerBIChange(
                    target=measure,
                    target_type="measure",
                    action="Validate",
                    detail="Measure sits on the modified table; confirm totals are unchanged after the refresh.",
                )
            )
        for visual in dict.fromkeys(plan.impacted_visuals):
            plan.changes.append(
                PowerBIChange(
                    target=visual,
                    target_type="visual",
                    action="Review field placement",
                    detail=f"Candidate visual for surfacing '{friendly}'.",
                )
            )
        plan.changes.append(
            PowerBIChange(
                target=request.report,
                target_type="report",
                action="Publish validation",
                detail="Publish to the workspace and compare totals against the pre-change snapshot.",
            )
        )

        plan.impacted_measures = list(dict.fromkeys(plan.impacted_measures))
        plan.impacted_relationships = list(dict.fromkeys(plan.impacted_relationships))
        plan.impacted_visuals = list(dict.fromkeys(plan.impacted_visuals))
        context.power_bi = plan
        return (
            f"{len(plan.changes)} Power BI actions for dataset '{dataset_name}': "
            f"{len(plan.impacted_measures)} measures, {len(plan.impacted_visuals)} visuals to review"
        )

    @staticmethod
    def _visual_uses_table(visual: dict, table: dict, measures: list[str]) -> bool:
        fields = set(visual.get("columns", []) + visual.get("rows", []) + visual.get("axis", []))
        if fields & set(table.get("columns", [])):
            return True
        return bool(set(visual.get("values", [])) & set(measures))

    @staticmethod
    def _tmdl(table_name: str, column: str, friendly: str, data_type: str) -> str:
        base = data_type.upper().split("(")[0]
        dax_type = _DAX_TYPES.get(base, "string")
        summarize = "none" if dax_type in {"string", "dateTime", "boolean"} else "sum"
        return (
            f"table '{table_name}'\n"
            f"\tcolumn {column}\n"
            f"\t\tdataType: {dax_type}\n"
            f"\t\tsourceColumn: {column}\n"
            f"\t\tdisplayName: {friendly}\n"
            f"\t\tsummarizeBy: {summarize}\n"
            f"\t\tisHidden: false\n"
        )
