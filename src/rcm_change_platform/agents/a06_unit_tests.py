"""Agent 6 - Unit Test Generation.

Derives the data quality suite from the catalog: population, row count parity,
null, duplicate, datatype, domain and source-to-target value checks. Each case
carries a machine readable assertion so the same SQL that ships in
``Unit_Tests.sql`` is what the sandbox executes.
"""

from __future__ import annotations

from ..context import ChangeContext
from ..models import ImpactAction, Severity, TestCase, TestRun, TestStatus, TestSuite
from ..sandbox import runner
from ..sandbox.warehouse import SandboxError, skipped_results
from .base import Agent


class UnitTestGenerationAgent(Agent):
    name = "unit_test_generation"
    step = 6

    def execute(self, context: ChangeContext) -> str:
        metadata, impact = context.metadata, context.impact
        if metadata is None or metadata.column is None or impact is None:
            context.halt(self.name, "Unit test generation requires the metadata document and impact matrix.")
            return "missing prerequisites"

        suite = self._build_suite(context)
        context.unit_suite = suite

        if not context.options.execute_tests:
            context.unit_run = TestRun(suite=suite.name, results=skipped_results(suite.cases, "execution disabled"), executed=False)
            return f"generated {len(suite.cases)} unit tests (execution disabled)"

        try:
            sandbox = runner.candidate(context)
            results = sandbox.run_cases(suite.cases)
        except SandboxError as exc:
            context.unit_run = TestRun(suite=suite.name, results=skipped_results(suite.cases, str(exc)), executed=False)
            context.halt(self.name, f"Generated SQL failed to execute in the sandbox: {exc}")
            return "sandbox execution failed"

        run = TestRun(suite=suite.name, results=results)
        context.unit_run = run
        failures = [r.name for r in results if r.status is TestStatus.FAILED]
        if failures:
            context.warn(f"Unit test failures: {', '.join(failures)}")
        return (
            f"{run.count(TestStatus.PASSED)}/{len(results)} unit tests passed"
            + (f", failed: {', '.join(failures)}" if failures else "")
        )

    # -- suite construction ----------------------------------------------
    def _build_suite(self, context: ChangeContext) -> TestSuite:
        metadata, impact = context.metadata, context.impact
        assert metadata is not None and metadata.column is not None and impact is not None

        column = metadata.column.physical_column
        fact = impact.target_fact_table
        source_table = metadata.column.physical_table
        left_joined = impact.join_plan.get("strategy") == "new_join"
        nullable = metadata.column.nullable or left_joined

        suite = TestSuite(
            name=f"unit_tests_{column}",
            description=f"Data quality suite for {fact}.{column}",
        )

        suite.cases.append(
            TestCase(
                name="column_population",
                category="Column Population",
                sql=f"SELECT COUNT(*) AS populated_rows\nFROM {fact}\nWHERE {column} IS NOT NULL;",
                expectation="at least one populated row",
                assertion={"kind": "scalar", "operator": "gte", "expected": 1},
                severity=Severity.BLOCKING,
            )
        )

        suite.cases.append(
            TestCase(
                name="null_validation",
                category="Null Validation",
                sql=f"SELECT COUNT(*) AS null_rows\nFROM {fact}\nWHERE {column} IS NULL;",
                expectation="0 records" if not nullable else "nulls are reported for review (LEFT JOIN or nullable source)",
                assertion={"kind": "scalar", "operator": "eq", "expected": 0}
                if not nullable
                else {"kind": "scalar", "operator": "gte", "expected": 0},
                severity=Severity.BLOCKING if not nullable else Severity.WARNING,
            )
        )

        driving_table = self._driving_table(context)
        if driving_table:
            suite.cases.append(
                TestCase(
                    name="row_count_validation",
                    category="Row Count Validation",
                    sql=f"SELECT COUNT(*) AS target_rows FROM {fact};",
                    expectation=f"matches the source row count from {driving_table}",
                    assertion={
                        "kind": "compare_scalar",
                        "operator": "eq",
                        "expected_sql": f"SELECT COUNT(*) AS source_rows FROM {driving_table};",
                    },
                    severity=Severity.BLOCKING,
                )
            )

        table = context.repo.table(fact) or {}
        business_keys = table.get("business_keys", [])
        if business_keys:
            key_list = ", ".join(business_keys)
            suite.cases.append(
                TestCase(
                    name="duplicate_validation",
                    category="Duplicate Validation",
                    sql=(
                        "SELECT COUNT(*) AS duplicate_keys\nFROM (\n"
                        f"    SELECT {key_list}\n    FROM {fact}\n"
                        f"    GROUP BY {key_list}\n    HAVING COUNT(*) > 1\n) duplicates;"
                    ),
                    expectation="0 records",
                    assertion={"kind": "scalar", "operator": "eq", "expected": 0},
                    severity=Severity.BLOCKING,
                )
            )

        length = self._varchar_length(metadata.column.data_type)
        if length:
            suite.cases.append(
                TestCase(
                    name="datatype_validation",
                    category="Data Type Validation",
                    sql=(
                        f"SELECT COUNT(*) AS oversized_values\nFROM {fact}\n"
                        f"WHERE {column} IS NOT NULL\n  AND LENGTH({column}) > {length};"
                    ),
                    expectation=f"0 records exceeding {metadata.column.data_type}",
                    assertion={"kind": "scalar", "operator": "eq", "expected": 0},
                    severity=Severity.BLOCKING,
                )
            )

        if metadata.column.domain_values:
            values = ", ".join(f"'{value}'" for value in metadata.column.domain_values)
            suite.cases.append(
                TestCase(
                    name="domain_validation",
                    category="Domain Validation",
                    sql=(
                        f"SELECT COUNT(*) AS out_of_domain\nFROM {fact}\n"
                        f"WHERE {column} IS NOT NULL\n  AND {column} NOT IN ({values});"
                    ),
                    expectation="0 records outside the certified domain",
                    assertion={"kind": "scalar", "operator": "eq", "expected": 0},
                    severity=Severity.BLOCKING,
                )
            )

        parity = self._source_parity_case(context, fact, source_table, column)
        if parity:
            suite.cases.append(parity)

        for item in impact.items:
            view = context.repo.view(item.object_name)
            if view and item.action is ImpactAction.MODIFY:
                suite.cases.append(
                    TestCase(
                        name=f"view_exposure_{item.object_name.split('.')[-1]}",
                        category="Reporting Layer Exposure",
                        sql=(
                            f"SELECT COUNT(*) AS exposed_rows\nFROM {item.object_name}\n"
                            f"WHERE {column} IS NOT NULL;"
                        ),
                        expectation="view compiles and exposes the new column",
                        assertion={"kind": "scalar", "operator": "gte", "expected": 0 if nullable else 1},
                        severity=Severity.BLOCKING,
                    )
                )
        return suite

    @staticmethod
    def _varchar_length(data_type: str) -> int | None:
        upper = data_type.upper()
        if not upper.startswith(("VARCHAR", "CHAR")):
            return None
        digits = "".join(ch for ch in upper.split("(")[-1] if ch.isdigit())
        return int(digits) if digits else None

    def _driving_table(self, context: ChangeContext) -> str:
        impact = context.impact
        assert impact is not None
        routines = context.repo.routines_writing(impact.target_fact_table)
        if not routines:
            return ""
        for table_name in routines[0].get("reads", []):
            table = context.repo.table(table_name)
            if table and table.get("layer") == "staging":
                return table_name
        return routines[0].get("reads", [""])[0]

    def _source_parity_case(self, context: ChangeContext, fact: str, source_table: str, column: str) -> TestCase | None:
        relationship = context.repo.relationship_between(fact, source_table)
        if not relationship:
            return None
        if relationship["from_table"] == fact:
            fact_column, source_column = relationship["from_column"], relationship["to_column"]
        else:
            fact_column, source_column = relationship["to_column"], relationship["from_column"]
        return TestCase(
            name="source_to_target_parity",
            category="Source to Target Validation",
            sql=(
                "SELECT COUNT(*) AS mismatched_rows\n"
                f"FROM {fact} f\n"
                f"JOIN {source_table} s ON s.{source_column} = f.{fact_column}\n"
                f"WHERE COALESCE(f.{column}, '~') <> COALESCE(s.{column}, '~');"
            ),
            expectation="0 records where the fact value differs from the source dimension",
            assertion={"kind": "scalar", "operator": "eq", "expected": 0},
            severity=Severity.BLOCKING,
        )
