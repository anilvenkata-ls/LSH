from __future__ import annotations

import pytest

from rcm_change_platform.models import Severity
from rcm_change_platform.models import TestCase as Case
from rcm_change_platform.sandbox import SandboxError, WarehouseSandbox, skipped_results
from rcm_change_platform.sandbox import runner


@pytest.fixture
def loaded(repo):
    with WarehouseSandbox(repo) as sandbox:
        sandbox.build()
        sandbox.run_etl()
        yield sandbox


def test_translation_quotes_qualified_names(repo):
    sandbox = WarehouseSandbox(repo)
    translated = sandbox.translate("SELECT * FROM rcm.fact_ar f JOIN rcm.dim_patient p ON 1=1")
    assert '"rcm.fact_ar"' in translated and '"rcm.dim_patient"' in translated
    assert sandbox.translate("CREATE OR REPLACE VIEW rcm.vw_ar_detail AS SELECT 1").startswith("CREATE VIEW")
    sandbox.close()


def test_etl_populates_the_fact_table_from_staging(loaded):
    assert loaded.scalar("SELECT COUNT(*) FROM rcm.fact_ar") == 12
    assert loaded.scalar("SELECT COUNT(*) FROM staging.stg_ar_transactions") == 12
    assert round(loaded.scalar("SELECT SUM(balance) FROM rcm.fact_ar"), 2) == 6490.00


def test_views_are_materialised_and_queryable(loaded):
    assert loaded.scalar("SELECT COUNT(*) FROM rcm.vw_ar_detail") == 12
    buckets = {row[0] for row in loaded.query("SELECT aging_bucket FROM rcm.vw_ar_aging_summary")}
    assert buckets == {"0-30", "31-60", "61-90", "90+"}


def test_assertion_operators(loaded):
    passing = Case(
        name="zero_nulls",
        category="Null Validation",
        sql="SELECT COUNT(*) FROM rcm.fact_ar WHERE balance IS NULL",
        expectation="0 records",
        assertion={"kind": "scalar", "operator": "eq", "expected": 0},
    )
    failing = Case(
        name="impossible",
        category="Null Validation",
        sql="SELECT COUNT(*) FROM rcm.fact_ar",
        expectation="0 records",
        assertion={"kind": "scalar", "operator": "eq", "expected": 0},
    )
    compare = Case(
        name="row_parity",
        category="Row Count Validation",
        sql="SELECT COUNT(*) FROM rcm.fact_ar",
        expectation="matches staging",
        assertion={
            "kind": "compare_scalar",
            "operator": "eq",
            "expected_sql": "SELECT COUNT(*) FROM staging.stg_ar_transactions",
        },
    )
    empty = Case(
        name="no_rows",
        category="Duplicate Validation",
        sql="SELECT claim_id FROM rcm.fact_ar GROUP BY claim_id HAVING COUNT(*) > 1",
        expectation="no rows",
        assertion={"kind": "empty"},
    )
    statuses = {case.name: loaded.run_case(case).status.value for case in (passing, failing, compare, empty)}
    assert statuses == {"zero_nulls": "passed", "impossible": "failed", "row_parity": "passed", "no_rows": "passed"}


def test_broken_sql_is_reported_as_an_error_not_an_exception(loaded):
    case = Case(
        name="broken",
        category="Null Validation",
        sql="SELECT COUNT(*) FROM rcm.table_that_does_not_exist",
        expectation="0 records",
        assertion={"kind": "scalar", "operator": "eq", "expected": 0},
    )
    result = loaded.run_case(case)
    assert result.status.value == "error"
    assert "no such table" in result.message


def test_execute_script_raises_sandbox_error(loaded):
    with pytest.raises(SandboxError):
        loaded.execute_script("ALTER TABLE rcm.nope ADD COLUMN x TEXT;")


def test_reconcile_detects_drift(loaded):
    metrics = {"balance": "SELECT COALESCE(SUM(balance), 0) FROM rcm.fact_ar"}
    before = loaded.snapshot(metrics)
    loaded.connection.execute('DELETE FROM "rcm.fact_ar" WHERE claim_id = \'CLM-0004\'')
    report = loaded.reconcile(metrics, before)
    assert not report.balanced
    assert report.lines[0].difference != 0


def test_skipped_results_preserve_case_metadata():
    case = Case(name="c", category="Null Validation", sql="SELECT 1", expectation="x", severity=Severity.BLOCKING)
    result = skipped_results([case], "execution disabled")[0]
    assert result.status.value == "skipped"
    assert result.message == "execution disabled"


def test_view_output_columns_resolves_aliases(repo):
    detail = repo.view("rcm.vw_ar_detail")["definition"]
    summary = repo.view("rcm.vw_ar_aging_summary")["definition"]
    assert "balance" in runner.view_output_columns(detail)
    assert runner.view_output_columns(summary) == ["aging_bucket", "claim_count", "total_balance"]
