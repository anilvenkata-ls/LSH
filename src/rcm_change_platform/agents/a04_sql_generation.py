"""Agent 4 - SQL Change Generation.

Rewrites the impacted stored procedure and views with the new column, and emits
the forward migration plus a matching rollback. Edits are applied to the real
object definitions from the catalog using the structure aware helpers in
:mod:`rcm_change_platform.sqlkit`, so the output is a diff a reviewer can read
rather than a regenerated file.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .. import sqlkit
from ..context import ChangeContext
from ..models import ImpactAction, ObjectChange, SqlChangeSet
from .base import Agent


class SqlChangeGenerationAgent(Agent):
    name = "sql_change_generation"
    step = 4

    def execute(self, context: ChangeContext) -> str:
        request, metadata, impact = context.request, context.metadata, context.impact
        if request is None or metadata is None or metadata.column is None or impact is None:
            context.halt(self.name, "SQL generation requires the metadata document and impact matrix.")
            return "missing prerequisites"

        column = metadata.column.physical_column
        data_type = metadata.column.data_type
        fact_table = impact.target_fact_table
        change_set = SqlChangeSet(target_column=column, target_table=fact_table)

        needs_column = not context.repo.has_column(fact_table, column)
        if needs_column:
            change_set.migration_sql = self._migration(context, fact_table, column, data_type)
        else:
            change_set.notes.append(f"{fact_table}.{column} already exists; no ALTER TABLE was generated.")

        for item in impact.items:
            if item.action is not ImpactAction.MODIFY:
                continue
            if item.object_type == "stored_procedure":
                change_set.object_changes.append(self._procedure_change(context, item.object_name, column))
            elif item.object_type == "view":
                change_set.object_changes.append(self._view_change(context, item.object_name, column, fact_table))

        change_set.rollback_sql = self._rollback(context, change_set, fact_table, column, needs_column)
        change_set.notes.extend(impact.warnings)
        context.change_set = change_set

        changed = ", ".join(change.object_name for change in change_set.object_changes) or "none"
        return f"generated migration for {fact_table}.{column} and edits to {changed}"

    # -- statement builders ---------------------------------------------
    def _header(self, context: ChangeContext, title: str) -> str:
        request = context.request
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return (
            f"-- {title}\n"
            f"-- Request: {request.request_id} - {request.raw_request}\n"
            f"-- Generated: {stamp} by the RCM change automation platform\n"
            f"-- Review required before execution.\n"
        )

    def _migration(self, context: ChangeContext, fact_table: str, column: str, data_type: str) -> str:
        loader = context.repo.routines_writing(fact_table)
        reload_hint = (
            f"\n-- Backfill: CALL {loader[0]['name']}();  -- full snapshot reload repopulates history\n"
            if loader
            else ""
        )
        return (
            self._header(context, f"Forward migration: add {column} to {fact_table}")
            + f"\nALTER TABLE {fact_table}\n    ADD COLUMN {column} {data_type};\n"
            + reload_hint
        )

    def _rollback(
        self,
        context: ChangeContext,
        change_set: SqlChangeSet,
        fact_table: str,
        column: str,
        dropped_column: bool,
    ) -> str:
        parts = [self._header(context, f"Rollback: remove {column} from {fact_table}")]
        for change in reversed(change_set.object_changes):
            parts.append(f"\n-- Restore {change.object_type} {change.object_name}\n{change.before.rstrip()}\n")
        if dropped_column:
            parts.append(f"\nALTER TABLE {fact_table}\n    DROP COLUMN {column};\n")
        loader = context.repo.routines_writing(fact_table)
        if loader:
            parts.append(f"\n-- CALL {loader[0]['name']}();  -- rebuild the snapshot with the original definition\n")
        return "".join(parts)

    # -- object edits -----------------------------------------------------
    def _procedure_change(self, context: ChangeContext, name: str, column: str) -> ObjectChange:
        routine = context.repo.routine(name)
        if routine is None:
            raise ValueError(f"Stored procedure {name} is missing from the catalog")
        before = routine["body"]
        join_plan = context.impact.join_plan if context.impact else {}
        after = before
        summary_bits = []

        if join_plan.get("strategy") == "new_join":
            after = sqlkit.add_join(after, join_plan["join_clause"])
            summary_bits.append(f"added {join_plan['join_clause'].split(' ON ')[0].strip()}")

        after = sqlkit.add_insert_column(after, column)
        after = sqlkit.add_projection_column(after, join_plan.get("expression", column))
        summary_bits.append(f"projected {join_plan.get('expression', column)} into {column}")

        return ObjectChange(
            object_name=name,
            object_type="stored_procedure",
            before=before,
            after=after,
            diff=sqlkit.unified_diff(before, after, f"{name}.sql"),
            summary="; ".join(summary_bits),
        )

    def _view_change(self, context: ChangeContext, name: str, column: str, fact_table: str) -> ObjectChange:
        view = context.repo.view(name)
        if view is None:
            raise ValueError(f"View {name} is missing from the catalog")
        before = view["definition"]
        alias = sqlkit.alias_for_table(before, fact_table)
        expression = f"{alias}.{column}" if alias else column
        after = sqlkit.add_projection_column(before, expression)
        return ObjectChange(
            object_name=name,
            object_type="view",
            before=before,
            after=after,
            diff=sqlkit.unified_diff(before, after, f"{name}.sql"),
            summary=f"selected {expression}",
        )


def deployment_script(context: ChangeContext) -> str:
    """Assemble the deployable script from the generated change set."""

    change_set = context.change_set
    if change_set is None:
        return ""
    parts: list[str] = []
    if change_set.migration_sql:
        parts.append(change_set.migration_sql.rstrip())
    for change in change_set.object_changes:
        parts.append(f"\n-- {change.object_type}: {change.object_name} ({change.summary})\n{change.after.rstrip()}")
    loader = context.repo.routines_writing(change_set.target_table)
    if loader:
        parts.append(f"\n-- Reload the snapshot so the new column is populated\nCALL {loader[0]['name']}();")
    return "\n".join(parts) + "\n"
