from __future__ import annotations

from rcm_change_platform.agents import (
    ImpactAnalysisAgent,
    IntegrationTestingAgent,
    MetadataDiscoveryAgent,
    RequestIntakeAgent,
    SqlChangeGenerationAgent,
    UnitTestGenerationAgent,
)
from rcm_change_platform.models import Severity
from rcm_change_platform.models import TestStatus as Status

THROUGH_UNIT = (
    RequestIntakeAgent,
    MetadataDiscoveryAgent,
    ImpactAnalysisAgent,
    SqlChangeGenerationAgent,
    UnitTestGenerationAgent,
)
THROUGH_INTEGRATION = THROUGH_UNIT + (IntegrationTestingAgent,)


def categories(suite) -> set[str]:
    return {case.category for case in suite.cases}


def test_unit_suite_covers_the_required_validations(run_agents):
    context = run_agents(THROUGH_UNIT)
    assert categories(context.unit_suite) >= {
        "Column Population",
        "Null Validation",
        "Row Count Validation",
        "Duplicate Validation",
        "Data Type Validation",
        "Domain Validation",
        "Source to Target Validation",
        "Reporting Layer Exposure",
    }


def test_unit_tests_execute_and_pass_against_the_generated_change(run_agents):
    context = run_agents(THROUGH_UNIT)
    assert context.unit_run.executed
    assert context.unit_run.passed
    assert context.unit_run.count(Status.PASSED) == len(context.unit_run.results)


def test_row_count_test_compares_against_the_staging_source(run_agents):
    context = run_agents(THROUGH_UNIT)
    case = context.unit_suite.case("row_count_validation")
    assert "staging.stg_ar_transactions" in case.assertion["expected_sql"]


def test_datatype_test_uses_the_declared_length(run_agents):
    context = run_agents(THROUGH_UNIT)
    assert "LENGTH(patient_financial_class) > 50" in context.unit_suite.case("datatype_validation").sql


def test_domain_test_lists_the_certified_values(run_agents):
    context = run_agents(THROUGH_UNIT)
    sql = context.unit_suite.case("domain_validation").sql
    assert "'Medicare'" in sql and "'Self Pay'" in sql


def test_left_joined_attribute_downgrades_the_null_check(run_agents):
    context = run_agents(THROUGH_UNIT, "Add Provider Specialty to the AR Aging Report")
    case = context.unit_suite.case("null_validation")
    assert case.severity is Severity.WARNING
    assert context.unit_suite.case("domain_validation") is None
    assert context.unit_run.passed


def test_generation_only_mode_skips_execution(run_agents):
    context = run_agents(THROUGH_UNIT, execute_tests=False)
    assert context.unit_suite.cases
    assert not context.unit_run.executed
    assert all(result.status is Status.SKIPPED for result in context.unit_run.results)


def test_unit_agent_halts_when_generated_sql_cannot_execute(run_agents, make_repo):
    def corrupt_procedure(payload):
        for routine in payload["information_schema"]["routines"]:
            if routine["name"] == "rcm.sp_load_ar_fact":
                routine["body"] = routine["body"].replace("p.patient_id = s.patient_id", "p.patient_id = s.missing_col")

    context = run_agents(THROUGH_UNIT, repo=make_repo(corrupt_procedure))
    assert context.halted_by == "unit_test_generation"
    assert any("sandbox" in warning for warning in context.warnings)


def test_integration_reconciles_every_financial_metric(run_agents):
    context = run_agents(THROUGH_INTEGRATION)
    metrics = {line.metric for line in context.reconciliation.lines}
    assert "rcm.fact_ar SUM(charge_amount)" in metrics
    assert "rcm.fact_ar SUM(payment_amount)" in metrics
    assert "rcm.fact_ar SUM(adjustment_amount)" in metrics
    assert "rcm.fact_ar SUM(denial_amount)" in metrics
    assert "rcm.fact_ar SUM(balance)" in metrics
    assert "rcm.vw_ar_detail SUM(balance)" in metrics
    assert context.reconciliation.balanced


def test_integration_run_includes_reporting_parity(run_agents):
    context = run_agents(THROUGH_INTEGRATION)
    names = {result.name for result in context.integration_run.results}
    assert "parity::rcm.vw_ar_detail::row_count" in names
    assert "parity::rcm.vw_ar_aging_summary::total_balance" in names
    assert context.integration_run.passed


def test_reconciliation_failure_is_surfaced_as_a_warning(run_agents):
    """A generated change that silently drops rows must fail the release gate."""

    context = run_agents(THROUGH_UNIT[:-1])
    change = context.change_set.change_for("rcm.sp_load_ar_fact")
    change.after = change.after.replace(
        "JOIN rcm.dim_payer pay ON pay.payer_id = s.payer_id;",
        "JOIN rcm.dim_payer pay ON pay.payer_id = s.payer_id\n    WHERE s.denial_amount = 0;",
    )
    IntegrationTestingAgent().run(context)

    assert not context.reconciliation.balanced
    assert any("reconciliation drift" in warning for warning in context.warnings)
    failed = [r.name for r in context.integration_run.results if r.status is Status.FAILED]
    assert any("SUM(balance)" in name for name in failed)
