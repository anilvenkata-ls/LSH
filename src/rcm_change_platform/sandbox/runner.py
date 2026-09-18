"""Builds the baseline and candidate warehouses used by the testing agents."""

from __future__ import annotations

import re

from .. import sqlkit
from ..context import ChangeContext
from .warehouse import WarehouseSandbox

_BASELINE = "sandbox.baseline"
_CANDIDATE = "sandbox.candidate"

FINANCIAL_COLUMNS = (
    "charge_amount",
    "payment_amount",
    "adjustment_amount",
    "denial_amount",
    "balance",
)


def baseline(context: ChangeContext) -> WarehouseSandbox:
    """The warehouse as it exists today, with the ETL replayed."""

    sandbox = context.scratch.get(_BASELINE)
    if sandbox is None:
        sandbox = WarehouseSandbox(context.repo).build()
        sandbox.run_etl()
        context.scratch[_BASELINE] = sandbox
    return sandbox


def candidate(context: ChangeContext) -> WarehouseSandbox:
    """The warehouse with the generated change applied and the ETL replayed."""

    sandbox = context.scratch.get(_CANDIDATE)
    if sandbox is None:
        sandbox = WarehouseSandbox(context.repo).build()
        if context.change_set is not None:
            sandbox.apply_change_set(context.change_set)
        sandbox.run_etl()
        context.scratch[_CANDIDATE] = sandbox
    return sandbox


def financial_metrics(context: ChangeContext) -> dict[str, str]:
    """Reconciliation metrics derived from the catalog, not hard coded.

    Every monetary column on the impacted fact table plus the row counts of the
    fact table and of each view feeding the report. These are the numbers the
    business checks after a report change.
    """

    impact = context.impact
    if impact is None:
        return {}
    fact = impact.target_fact_table
    metrics: dict[str, str] = {f"{fact} row count": f"SELECT COUNT(*) FROM {fact}"}

    columns = {column.name for column in context.repo.columns(fact)}
    for column in FINANCIAL_COLUMNS:
        if column in columns:
            metrics[f"{fact} SUM({column})"] = f"SELECT COALESCE(SUM({column}), 0) FROM {fact}"

    table = context.repo.table(fact) or {}
    for key in table.get("business_keys", []):
        metrics[f"{fact} DISTINCT({key})"] = f"SELECT COUNT(DISTINCT {key}) FROM {fact}"

    for item in impact.items:
        view = context.repo.view(item.object_name)
        if not view:
            continue
        metrics[f"{item.object_name} row count"] = f"SELECT COUNT(*) FROM {item.object_name}"
        for column in view_output_columns(view.get("definition", "")):
            if column in {"balance", "total_balance"}:
                metrics[f"{item.object_name} SUM({column})"] = (
                    f"SELECT COALESCE(SUM({column}), 0) FROM {item.object_name}"
                )
    return metrics


def view_output_columns(definition: str) -> list[str]:
    """Output column names of a view: the alias, or the trailing identifier."""

    try:
        start, end = sqlkit.projection_span(definition)
    except sqlkit.SqlEditError:
        return []
    columns = []
    for item in sqlkit.split_projection(definition[start:end]):
        expression = item.strip().rstrip(",")
        if not expression:
            continue
        alias_match = re.search(r"\bAS\s+([A-Za-z_][A-Za-z_0-9]*)\s*$", expression, re.IGNORECASE)
        if alias_match:
            columns.append(alias_match.group(1).lower())
            continue
        tail = expression.split()[-1]
        columns.append(tail.split(".")[-1].lower())
    return columns
