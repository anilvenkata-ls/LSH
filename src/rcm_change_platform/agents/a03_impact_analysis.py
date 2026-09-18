"""Agent 3 - Impact Analysis.

Walks the lineage graph in both directions to produce the impact matrix: which
database objects, ETL components and Power BI artifacts must change, refresh or
simply be reviewed. It also produces the join plan that the SQL generation agent
needs, i.e. how the attribute reaches the fact table that feeds the report.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from ..catalog.lineage import CONTROL, DATA
from ..context import ChangeContext
from ..models import ImpactAction, ImpactItem, ImpactMatrix
from ..sqlkit import alias_for_table, suggest_alias
from .base import Agent


class ImpactAnalysisAgent(Agent):
    name = "impact_analysis"
    step = 3

    def execute(self, context: ChangeContext) -> str:
        request = context.request
        metadata = context.metadata
        if request is None or metadata is None or metadata.column is None:
            context.halt(self.name, "Impact analysis requires a resolved request and column.")
            return "missing prerequisites"

        repo, graph = context.repo, context.graph
        report_name = request.report
        source_table = metadata.column.physical_table
        column_name = metadata.column.physical_column

        report_ancestors = graph.upstream(report_name, kinds=(DATA,))
        fact_table = self._target_fact_table(context, report_name, report_ancestors)
        if not fact_table:
            context.halt(self.name, f"No fact table feeding '{report_name}' was found in the lineage graph.")
            return "no fact table in lineage"

        loader = self._loading_routine(context, fact_table)
        if loader is None:
            context.halt(self.name, f"No stored procedure loads {fact_table}; cannot automate the change.")
            return "no loading procedure"

        join_plan = self._join_plan(context, loader, source_table, column_name)
        matrix = ImpactMatrix(
            report=report_name,
            source_table=source_table,
            target_fact_table=fact_table,
            join_plan=join_plan,
        )
        if join_plan["strategy"] == "unreachable":
            matrix.warnings.append(
                f"{source_table} is not joinable to the inputs of {loader['name']} using the recorded relationships."
            )
            context.impact = matrix
            context.halt(self.name, matrix.warnings[-1])
            return "source table not joinable"

        on_path = [node for node in graph.downstream(fact_table, kinds=(DATA,)) if node in set(report_ancestors)]
        other_consumers = [
            node
            for node in graph.downstream(fact_table, kinds=(DATA,))
            if node not in set(report_ancestors) and node != report_name
        ]

        self._add_source_items(context, matrix, source_table, join_plan)
        self._add_warehouse_items(context, matrix, loader, fact_table, column_name, on_path)
        self._add_reporting_items(context, matrix, report_name, on_path)
        self._add_etl_items(context, matrix, loader["name"], fact_table, on_path)
        self._add_review_items(context, matrix, other_consumers)

        matrix.propagation_path = self._propagation_path(context, source_table, report_name, fact_table, loader["name"])
        context.impact = matrix

        modifies = [item.object_name for item in matrix.items if item.action is ImpactAction.MODIFY]
        return f"{len(matrix.items)} impacted objects, {len(modifies)} require code changes: {', '.join(modifies)}"

    # -- discovery helpers ---------------------------------------------
    def _target_fact_table(self, context: ChangeContext, report: str, ancestors: list[str]) -> str:
        facts = [
            name
            for name in ancestors
            if (table := context.repo.table(name)) and table.get("layer") == "fact"
        ]
        if not facts:
            return ""
        facts.sort(key=lambda name: len(context.graph.shortest_path(name, report)) or 99)
        return facts[0]

    def _loading_routine(self, context: ChangeContext, fact_table: str) -> dict[str, Any] | None:
        routines = context.repo.routines_writing(fact_table)
        return routines[0] if routines else None

    def _join_plan(self, context: ChangeContext, loader: dict, source_table: str, column: str) -> dict[str, Any]:
        """Work out how the loading procedure can reach ``source_table.column``."""

        body = loader.get("body", "")
        reads = loader.get("reads", [])
        if source_table in reads:
            alias = alias_for_table(body, source_table) or source_table.split(".")[-1]
            return {
                "strategy": "existing_join",
                "source_table": source_table,
                "alias": alias,
                "expression": f"{alias}.{column}",
                "detail": f"{loader['name']} already joins {source_table} as '{alias}'.",
            }

        for read_table in reads:
            relationship = context.repo.relationship_between(source_table, read_table)
            if not relationship:
                continue
            existing_alias = alias_for_table(body, read_table) or read_table.split(".")[-1]
            new_alias = suggest_alias(body, source_table)
            if relationship["from_table"] == source_table:
                source_column, other_column = relationship["from_column"], relationship["to_column"]
            else:
                source_column, other_column = relationship["to_column"], relationship["from_column"]
            join_clause = (
                f"LEFT JOIN {source_table} {new_alias} "
                f"ON {new_alias}.{source_column} = {existing_alias}.{other_column}"
            )
            return {
                "strategy": "new_join",
                "source_table": source_table,
                "alias": new_alias,
                "expression": f"{new_alias}.{column}",
                "join_clause": join_clause,
                "join_to": read_table,
                "detail": (
                    f"{source_table} is not joined in {loader['name']}; it reaches the load through "
                    f"{read_table}.{other_column} and a LEFT JOIN is required."
                ),
            }

        return {"strategy": "unreachable", "source_table": source_table, "detail": "no relationship found"}

    # -- matrix construction --------------------------------------------
    def _add(self, context: ChangeContext, matrix: ImpactMatrix, name: str, action: ImpactAction, rationale: str, risk: str = "low") -> None:
        matrix.items.append(
            ImpactItem(
                object_name=name,
                object_type=context.repo.object_type(name),
                action=action,
                layer=context.repo.layer_of(name),
                rationale=rationale,
                owner=self._owner(context, name),
                risk=risk,
            )
        )

    @staticmethod
    def _owner(context: ChangeContext, name: str) -> str:
        report = context.repo.report(name)
        if report:
            return report.get("owner", "")
        dataset = context.repo.dataset(name)
        if dataset:
            return dataset.get("workspace", "")
        return ""

    def _add_source_items(self, context: ChangeContext, matrix: ImpactMatrix, source_table: str, join_plan: dict) -> None:
        self._add(
            context,
            matrix,
            source_table,
            ImpactAction.NO_CHANGE,
            f"Provides the attribute. {join_plan['detail']}",
        )

    def _add_warehouse_items(
        self,
        context: ChangeContext,
        matrix: ImpactMatrix,
        loader: dict,
        fact_table: str,
        column: str,
        on_path: list[str],
    ) -> None:
        if context.repo.has_column(fact_table, column):
            self._add(
                context,
                matrix,
                fact_table,
                ImpactAction.NO_CHANGE,
                f"{column} already exists on the fact table.",
            )
            matrix.warnings.append(f"{fact_table}.{column} already exists; the migration will be skipped.")
        else:
            self._add(
                context,
                matrix,
                fact_table,
                ImpactAction.MODIFY,
                f"Add column {column} ({matrix.join_plan['strategy'].replace('_', ' ')}).",
                risk="medium",
            )
            self._add(
                context,
                matrix,
                loader["name"],
                ImpactAction.MODIFY,
                f"Populate {fact_table}.{column} in the INSERT and SELECT lists.",
                risk="medium",
            )

        for name in on_path:
            view = context.repo.view(name)
            if not view:
                continue
            if "GROUP BY" in view.get("definition", "").upper():
                self._add(
                    context,
                    matrix,
                    name,
                    ImpactAction.REVIEW,
                    f"Aggregate view: adding {column} would change the grain, so it needs a business decision "
                    "rather than an automated edit.",
                    risk="medium",
                )
                matrix.warnings.append(
                    f"{name} aggregates rows; {column} was deliberately not added to avoid changing its grain."
                )
            else:
                self._add(
                    context,
                    matrix,
                    name,
                    ImpactAction.MODIFY,
                    f"Expose {column} to the reporting layer.",
                )

    def _add_reporting_items(self, context: ChangeContext, matrix: ImpactMatrix, report: str, on_path: list[str]) -> None:
        for name in on_path:
            if any(flow["name"] == name for flow in context.repo.dataflows):
                self._add(context, matrix, name, ImpactAction.REFRESH, "Reload the dataflow so the new column lands in the dataset.")
            elif context.repo.dataset(name):
                self._add(
                    context,
                    matrix,
                    name,
                    ImpactAction.REFRESH,
                    "Refresh the semantic model to pick up the new column.",
                    risk="medium",
                )
        self._add(context, matrix, report, ImpactAction.MODIFY, "Surface the new column on the impacted visuals.")

    def _add_etl_items(self, context: ChangeContext, matrix: ImpactMatrix, loader_name: str, fact_table: str, on_path: list[str]) -> None:
        """Follow control edges so callers and their orchestrators are both listed."""

        seen = set(matrix.names())
        queue = deque([loader_name, fact_table, *on_path])
        while queue:
            target = queue.popleft()
            for edge in context.graph.outgoing(target, kinds=(CONTROL,)):
                component = edge.target
                if component in seen:
                    continue
                seen.add(component)
                queue.append(component)
                self._add(
                    context,
                    matrix,
                    component,
                    ImpactAction.REVIEW,
                    f"{edge.reason}; confirm the orchestration still succeeds after the change.",
                )

    def _add_review_items(self, context: ChangeContext, matrix: ImpactMatrix, other_consumers: list[str]) -> None:
        seen = set(matrix.names())
        for name in other_consumers:
            if name in seen:
                continue
            self._add(
                context,
                matrix,
                name,
                ImpactAction.REVIEW,
                "Consumes the modified fact table; the change is additive so no edit is expected.",
            )

    def _propagation_path(self, context: ChangeContext, source_table: str, report: str, fact_table: str, loader: str) -> list[str]:
        """The route the new value travels, which is not always the shortest one.

        A dimension often reaches a report twice: directly, because a reporting
        view joins it, and through the fact load. The change follows the second
        route, so the path is anchored on the loader and the fact table.
        """

        downstream = context.graph.shortest_path(fact_table, report)
        if source_table == fact_table:
            return downstream
        return [source_table, loader, *downstream]
