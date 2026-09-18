"""An executable stand-in for the Redshift warehouse.

Generated SQL is only trustworthy if something runs it. The sandbox materialises
the catalog (tables, seeded rows, views, stored procedure bodies) into an
in-memory SQLite database, replays the ETL, applies a generated change set and
re-runs the ETL so the platform can prove that a change compiles, populates the
new column and leaves the financial totals untouched.

SQLite has no schemas or stored procedures, so qualified object names are mapped
to quoted identifiers and procedure bodies are executed statement by statement.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any, Iterable, Sequence

from ..catalog.repository import MetadataRepository
from ..models import (
    ReconciliationLine,
    ReconciliationReport,
    Severity,
    TestCase,
    TestResult,
    TestStatus,
)
from .. import sqlkit

_TYPE_MAP = {
    "DATE": "TEXT",
    "TIMESTAMP": "TEXT",
    "BOOLEAN": "INTEGER",
}


class SandboxError(RuntimeError):
    pass


def _sqlite_type(data_type: str) -> str:
    base = data_type.upper().strip()
    if base.startswith("VARCHAR") or base.startswith("CHAR"):
        return "TEXT"
    for key, mapped in _TYPE_MAP.items():
        if base.startswith(key):
            return mapped
    return base


class WarehouseSandbox:
    """In-memory execution environment for catalog objects and generated SQL."""

    def __init__(self, repo: MetadataRepository):
        self.repo = repo
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        self._procedure_bodies: dict[str, str] = {
            routine["name"]: routine["body"] for routine in repo.routines
        }
        self._view_definitions: dict[str, str] = {
            view["name"]: view["definition"] for view in repo.views
        }
        self._extra_columns: dict[str, list[tuple[str, str]]] = {}
        self.applied_statements: list[str] = []

    # -- lifecycle ----------------------------------------------------
    def __enter__(self) -> "WarehouseSandbox":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    # -- name translation ---------------------------------------------
    def _object_names(self) -> list[str]:
        names = [t["name"] for t in self.repo.tables] + list(self._view_definitions)
        return sorted(names, key=len, reverse=True)

    def translate(self, sql: str) -> str:
        """Rewrite warehouse SQL into something SQLite can execute."""

        translated = sql
        for name in self._object_names():
            pattern = re.compile(rf'(?<!["\w.]){re.escape(name)}(?![\w."])')
            translated = pattern.sub(f'"{name}"', translated)
        translated = re.sub(r"CREATE\s+OR\s+REPLACE\s+VIEW", "CREATE VIEW", translated, flags=re.IGNORECASE)
        translated = re.sub(r"\bGETDATE\(\)", "CURRENT_DATE", translated, flags=re.IGNORECASE)
        translated = re.sub(r"\bCURRENT_DATE\b", "date('now')", translated, flags=re.IGNORECASE)
        return translated

    # -- build --------------------------------------------------------
    def build(self) -> "WarehouseSandbox":
        for table in self.repo.tables:
            self._create_table(table)
        self._seed_rows()
        for name in self._view_definitions:
            self._create_view(name)
        self.connection.commit()
        return self

    def _create_table(self, table: dict[str, Any]) -> None:
        name = table["name"]
        columns = [
            f'"{col["name"]}" {_sqlite_type(col["data_type"])}'
            + ("" if col.get("nullable", True) else " NOT NULL")
            for col in table.get("columns", [])
        ]
        columns += [f'"{col}" {_sqlite_type(dtype)}' for col, dtype in self._extra_columns.get(name, [])]
        self.connection.execute(f'CREATE TABLE "{name}" ({", ".join(columns)})')

    def _seed_rows(self) -> None:
        for table_name, rows in self.repo.sample_data.items():
            if not rows:
                continue
            columns = list(rows[0])
            placeholders = ", ".join("?" for _ in columns)
            quoted = ", ".join(f'"{c}"' for c in columns)
            self.connection.executemany(
                f'INSERT INTO "{table_name}" ({quoted}) VALUES ({placeholders})',
                [tuple(row.get(col) for col in columns) for row in rows],
            )

    def _create_view(self, name: str) -> None:
        definition = self._view_definitions[name]
        self.connection.execute(f'DROP VIEW IF EXISTS "{name}"')
        self.connection.executescript(self.translate(definition))

    # -- change application -------------------------------------------
    def apply_change_set(self, change_set: Any) -> None:
        """Apply a :class:`SqlChangeSet` produced by the generation agent."""

        for statement in sqlkit.statements(change_set.migration_sql):
            if not sqlkit.is_executable(statement):
                continue
            self.execute_script(statement)
            self.applied_statements.append(statement)

        for change in change_set.object_changes:
            if change.object_type == "stored_procedure":
                self._procedure_bodies[change.object_name] = change.after
            elif change.object_type == "view":
                self._view_definitions[change.object_name] = change.after
                self._create_view(change.object_name)
        self.connection.commit()

    def execute_script(self, sql: str) -> None:
        try:
            self.connection.executescript(self.translate(sql))
        except sqlite3.Error as exc:  # pragma: no cover - surfaced to callers
            raise SandboxError(f"{exc} while executing: {sql.strip()[:400]}") from exc

    # -- ETL ----------------------------------------------------------
    def run_etl(self, procedures: Sequence[str] | None = None) -> list[str]:
        executed = []
        names = procedures if procedures is not None else list(self._procedure_bodies)
        for name in names:
            body = self._procedure_bodies.get(name)
            if body is None:
                raise SandboxError(f"Unknown procedure {name}")
            for statement in sqlkit.statements(sqlkit.procedure_body(body)):
                self.execute_script(statement)
            executed.append(name)
        self.connection.commit()
        return executed

    # -- queries -------------------------------------------------------
    def query(self, sql: str) -> list[sqlite3.Row]:
        try:
            cursor = self.connection.execute(self.translate(sql))
            return cursor.fetchall()
        except sqlite3.Error as exc:
            raise SandboxError(f"{exc} while querying: {sql.strip()[:400]}") from exc

    def scalar(self, sql: str) -> Any:
        rows = self.query(sql)
        if not rows:
            return None
        return rows[0][0]

    def snapshot(self, metrics: dict[str, str]) -> dict[str, float]:
        return {name: float(self.scalar(sql) or 0.0) for name, sql in metrics.items()}

    def table_columns(self, table_name: str) -> list[str]:
        rows = self.connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        return [row["name"] for row in rows]

    # -- assertions ----------------------------------------------------
    def run_case(self, case: TestCase) -> TestResult:
        assertion = case.assertion or {"kind": "scalar", "operator": "eq", "expected": 0}
        try:
            return self._evaluate(case, assertion)
        except SandboxError as exc:
            return TestResult(
                name=case.name,
                category=case.category,
                status=TestStatus.ERROR,
                expectation=case.expectation,
                actual="",
                message=str(exc),
                severity=case.severity,
            )

    def _evaluate(self, case: TestCase, assertion: dict[str, Any]) -> TestResult:
        kind = assertion.get("kind", "scalar")
        tolerance = float(assertion.get("tolerance", 0.0))
        if kind == "empty":
            rows = self.query(case.sql)
            passed = not rows
            actual = f"{len(rows)} row(s)"
        elif kind == "compare_scalar":
            left = self.scalar(case.sql)
            right = self.scalar(assertion["expected_sql"])
            passed = _compare(float(left or 0), float(right or 0), assertion.get("operator", "eq"), tolerance)
            actual = f"{left} vs {right}"
        else:
            value = self.scalar(case.sql)
            expected = float(assertion.get("expected", 0))
            numeric = float(value or 0)
            passed = _compare(numeric, expected, assertion.get("operator", "eq"), tolerance)
            actual = str(value)
        return TestResult(
            name=case.name,
            category=case.category,
            status=TestStatus.PASSED if passed else TestStatus.FAILED,
            expectation=case.expectation,
            actual=actual,
            message="" if passed else f"expected {case.expectation}, observed {actual}",
            severity=case.severity,
        )

    def run_cases(self, cases: Iterable[TestCase]) -> list[TestResult]:
        return [self.run_case(case) for case in cases]

    def reconcile(self, metrics: dict[str, str], before: dict[str, float], tolerance: float = 0.01) -> ReconciliationReport:
        after = self.snapshot(metrics)
        lines = [
            ReconciliationLine(metric=name, before=before.get(name, 0.0), after=after.get(name, 0.0), tolerance=tolerance)
            for name in metrics
        ]
        return ReconciliationReport(lines=lines)


def _compare(left: float, right: float, operator: str, tolerance: float) -> bool:
    if operator == "eq":
        return abs(left - right) <= tolerance
    if operator == "ne":
        return abs(left - right) > tolerance
    if operator == "gt":
        return left > right
    if operator == "gte":
        return left >= right - tolerance
    if operator == "lt":
        return left < right
    if operator == "lte":
        return left <= right + tolerance
    raise SandboxError(f"Unsupported assertion operator '{operator}'")


def skipped_results(cases: Iterable[TestCase], reason: str) -> list[TestResult]:
    return [
        TestResult(
            name=case.name,
            category=case.category,
            status=TestStatus.SKIPPED,
            expectation=case.expectation,
            message=reason,
            severity=case.severity if case.severity is not Severity.INFO else Severity.INFO,
        )
        for case in cases
    ]
