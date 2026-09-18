"""Agent 7 - Integration Testing.

Snapshots the financial metrics before the change, replays the ETL with the
change applied and compares the two. The rule the RCM team cares about is that
charges, payments, adjustments, denials and AR balances are identical before and
after a structural change; anything else is a release blocker.
"""

from __future__ import annotations

from ..context import ChangeContext
from ..models import (
    ReconciliationReport,
    Severity,
    TestCase,
    TestResult,
    TestRun,
    TestStatus,
    TestSuite,
)
from ..sandbox import runner
from ..sandbox.warehouse import SandboxError, skipped_results
from .base import Agent


class IntegrationTestingAgent(Agent):
    name = "integration_testing"
    step = 7

    def execute(self, context: ChangeContext) -> str:
        impact = context.impact
        if impact is None or context.change_set is None:
            context.halt(self.name, "Integration testing requires the impact matrix and change set.")
            return "missing prerequisites"

        metrics = runner.financial_metrics(context)
        suite = self._build_suite(context, metrics)
        context.integration_suite = suite

        if not context.options.execute_tests:
            context.integration_run = TestRun(
                suite=suite.name,
                results=skipped_results(suite.cases, "execution disabled"),
                executed=False,
            )
            context.reconciliation = ReconciliationReport(executed=False, notes=["execution disabled"])
            return f"generated {len(suite.cases)} integration checks (execution disabled)"

        try:
            before = runner.baseline(context).snapshot(metrics)
            candidate = runner.candidate(context)
            reconciliation = candidate.reconcile(metrics, before)
            parity_results = candidate.run_cases([c for c in suite.cases if c.assertion])
        except SandboxError as exc:
            context.integration_run = TestRun(
                suite=suite.name,
                results=skipped_results(suite.cases, str(exc)),
                executed=False,
            )
            context.reconciliation = ReconciliationReport(executed=False, notes=[str(exc)])
            context.halt(self.name, f"Integration run failed in the sandbox: {exc}")
            return "sandbox execution failed"

        context.reconciliation = reconciliation
        results = self._reconciliation_results(reconciliation) + parity_results
        run = TestRun(suite=suite.name, results=results)
        context.integration_run = run

        drifted = [line.metric for line in reconciliation.lines if not line.matched]
        if drifted:
            context.warn(
                "Financial reconciliation drift detected for: " + ", ".join(drifted)
            )
        failures = [r.name for r in results if r.status is TestStatus.FAILED]
        return (
            f"{run.count(TestStatus.PASSED)}/{len(results)} integration checks passed; "
            f"reconciliation {'balanced' if reconciliation.balanced else 'OUT OF BALANCE'}"
            + (f"; failed: {', '.join(failures)}" if failures else "")
        )

    # -- suite -----------------------------------------------------------
    def _build_suite(self, context: ChangeContext, metrics: dict[str, str]) -> TestSuite:
        impact = context.impact
        assert impact is not None
        fact = impact.target_fact_table
        suite = TestSuite(
            name="integration_tests",
            description="Before/after financial reconciliation and reporting layer parity",
        )

        for metric, sql in metrics.items():
            suite.cases.append(
                TestCase(
                    name=f"snapshot::{metric}",
                    category="Financial Reconciliation",
                    sql=f"-- Run before and after the change\n{sql};",
                    expectation="identical value before and after the change",
                    severity=Severity.BLOCKING,
                    assertion={},
                )
            )

        for item in impact.items:
            view = context.repo.view(item.object_name)
            if not view:
                continue
            output_columns = runner.view_output_columns(view.get("definition", ""))
            if "balance" in output_columns:
                suite.cases.append(
                    TestCase(
                        name=f"parity::{item.object_name}::balance",
                        category="Reporting Parity",
                        sql=f"SELECT COALESCE(SUM(balance), 0) FROM {item.object_name};",
                        expectation=f"equals COALESCE(SUM(balance), 0) from {fact}",
                        assertion={
                            "kind": "compare_scalar",
                            "operator": "eq",
                            "expected_sql": f"SELECT COALESCE(SUM(balance), 0) FROM {fact};",
                            "tolerance": 0.01,
                        },
                    )
                )
            if "total_balance" in output_columns:
                suite.cases.append(
                    TestCase(
                        name=f"parity::{item.object_name}::total_balance",
                        category="Reporting Parity",
                        sql=f"SELECT COALESCE(SUM(total_balance), 0) FROM {item.object_name};",
                        expectation=f"equals COALESCE(SUM(balance), 0) from {fact}",
                        assertion={
                            "kind": "compare_scalar",
                            "operator": "eq",
                            "expected_sql": f"SELECT COALESCE(SUM(balance), 0) FROM {fact};",
                            "tolerance": 0.01,
                        },
                    )
                )
            if not any(keyword in view.get("definition", "").upper() for keyword in ("GROUP BY", "DISTINCT")):
                suite.cases.append(
                    TestCase(
                        name=f"parity::{item.object_name}::row_count",
                        category="Reporting Parity",
                        sql=f"SELECT COUNT(*) FROM {item.object_name};",
                        expectation=f"equals the row count of {fact}",
                        assertion={
                            "kind": "compare_scalar",
                            "operator": "eq",
                            "expected_sql": f"SELECT COUNT(*) FROM {fact};",
                        },
                    )
                )
        return suite

    @staticmethod
    def _reconciliation_results(report: ReconciliationReport) -> list[TestResult]:
        return [
            TestResult(
                name=f"reconciliation::{line.metric}",
                category="Financial Reconciliation",
                status=TestStatus.PASSED if line.matched else TestStatus.FAILED,
                expectation="unchanged before and after",
                actual=f"before={line.before:,.2f} after={line.after:,.2f} delta={line.difference:,.2f}",
                message="" if line.matched else "value changed",
                severity=Severity.BLOCKING,
            )
            for line in report.lines
        ]
