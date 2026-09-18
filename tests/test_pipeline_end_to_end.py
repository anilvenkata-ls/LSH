from __future__ import annotations

import json
import zipfile
from pathlib import Path

from rcm_change_platform.cli import EXIT_BLOCKED, EXIT_HALTED, EXIT_OK, main

EXPECTED_ARTIFACTS = {
    "Requirement.md",
    "Technical_Design.md",
    "Impact_Analysis.xlsx",
    "Impact_Analysis.csv",
    "Generated_SQL.sql",
    "Unit_Tests.sql",
    "Integration_Tests.sql",
    "PR_Description.md",
    "Release_Notes.md",
    "Rollback_Script.sql",
    "Validation_Report.pdf",
    "Validation_Report.md",
    "PowerBI_Change_Plan.md",
    "Deployment_Checklist.md",
    "Run_Manifest.json",
}


def package_root(context) -> Path:
    return Path(context.package.root)


def test_full_run_produces_the_change_package(run_pipeline):
    context = run_pipeline()
    assert not context.halted
    assert [report.status for report in context.reports] == ["completed"] * 10
    assert set(context.package.files) == EXPECTED_ARTIFACTS
    root = package_root(context)
    assert all((root / name).exists() for name in EXPECTED_ARTIFACTS)


def test_full_run_is_deployment_ready(run_pipeline):
    context = run_pipeline()
    assert context.unit_run.passed and context.integration_run.passed
    assert context.reconciliation.balanced
    assert context.checklist.ready
    summary = context.summary()
    assert summary["deployment_ready"] is True
    assert summary["impacted_objects"]


def test_generated_sql_is_reviewable(run_pipeline):
    context = run_pipeline()
    sql = (package_root(context) / "Generated_SQL.sql").read_text()
    assert "ALTER TABLE rcm.fact_ar" in sql
    assert "CREATE OR REPLACE PROCEDURE rcm.sp_load_ar_fact" in sql
    assert "CREATE OR REPLACE VIEW rcm.vw_ar_detail" in sql
    assert sql.count("patient_financial_class") >= 4


def test_test_scripts_carry_expectations_and_results(run_pipeline):
    context = run_pipeline()
    unit = (package_root(context) / "Unit_Tests.sql").read_text()
    integration = (package_root(context) / "Integration_Tests.sql").read_text()
    assert "-- Expectation: 0 records" in unit
    assert "Sandbox result: passed" in unit
    assert "[Financial Reconciliation]" in integration
    assert "Run before and after the change" in integration


def test_documents_include_test_evidence_after_the_run(run_pipeline):
    context = run_pipeline()
    root = package_root(context)
    pr = (root / "PR_Description.md").read_text()
    assert "Financial reconciliation: balanced" in pr
    assert "Deployment readiness: **READY**" in pr
    design = (root / "Technical_Design.md").read_text()
    assert "Unit tests: " in design and "passed" in design


def test_manifest_captures_the_whole_run(run_pipeline):
    context = run_pipeline()
    manifest = json.loads((package_root(context) / "Run_Manifest.json").read_text())
    assert manifest["request"]["report"] == "AR Aging Report"
    assert manifest["metadata"]["column"]["physical_column"] == "patient_financial_class"
    assert len(manifest["agents"]) == 10
    assert manifest["checklist"]["blockers"] == []
    assert manifest["reconciliation"]["lines"]


def test_impact_workbook_has_every_sheet(run_pipeline):
    context = run_pipeline()
    with zipfile.ZipFile(package_root(context) / "Impact_Analysis.xlsx") as archive:
        workbook = archive.read("xl/workbook.xml").decode()
    for sheet in ("Impact Matrix", "Lineage Path", "Power BI", "Tests", "Reconciliation"):
        assert sheet in workbook


def test_generation_only_mode_still_packages_everything(run_pipeline):
    context = run_pipeline(execute_tests=False)
    assert not context.halted
    assert set(context.package.files) == EXPECTED_ARTIFACTS
    assert not context.checklist.ready
    assert "not executed" in (package_root(context) / "Validation_Report.md").read_text()


def test_halted_run_still_returns_clarifications(run_pipeline):
    context = run_pipeline("Add Zodiac Sign to the AR Aging Report")
    assert context.halted_by == "metadata_discovery"
    requirement = (package_root(context) / "Requirement.md").read_text()
    assert "Zodiac Sign" in requirement
    assert context.package.files


def test_provider_scenario_runs_with_a_new_join(run_pipeline):
    context = run_pipeline("Add Provider Specialty to the AR Aging Report")
    assert not context.halted
    assert context.impact.join_plan["strategy"] == "new_join"
    assert context.reconciliation.balanced
    sql = (package_root(context) / "Generated_SQL.sql").read_text()
    assert "LEFT JOIN rcm.dim_provider" in sql


def test_sandbox_connections_are_released(run_pipeline):
    context = run_pipeline()
    assert context.scratch == {}


def test_cli_exit_codes(tmp_path, capsys):
    assert main(["run", "Add Patient Financial Class to AR Aging", "-o", str(tmp_path / "ok")]) == EXIT_OK
    assert main(["run", "Add Patient Financial Class to AR Aging", "-o", str(tmp_path / "gen"), "--no-execute"]) == EXIT_BLOCKED
    assert main(["run", "Add Zodiac Sign to AR Aging", "-o", str(tmp_path / "halt")]) == EXIT_HALTED
    output = capsys.readouterr().out
    assert "RCM CHANGE AUTOMATION PLATFORM" in output
    assert "READY FOR DEPLOYMENT" in output


def test_cli_json_summary(tmp_path, capsys):
    main(["run", "Add Patient Financial Class to AR Aging", "-o", str(tmp_path / "json"), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["deployment_ready"] is True
    assert payload["request"]["requested_column"] == "Patient Financial Class"


def test_cli_catalog_and_lineage(capsys):
    assert main(["catalog", "reports"]) == EXIT_OK
    assert "AR Aging Report" in capsys.readouterr().out
    assert main(["lineage", "rcm.fact_ar"]) == EXIT_OK
    lineage = capsys.readouterr().out
    assert "-> rcm.vw_ar_detail" in lineage
    assert "<- rcm.sp_load_ar_fact" in lineage
    assert main(["lineage", "rcm.unknown_table"]) == EXIT_HALTED


def test_cli_accepts_an_external_metadata_directory(tmp_path):
    from rcm_change_platform.catalog.repository import SEEDS_DIR

    external = tmp_path / "metadata"
    external.mkdir()
    for seed in SEEDS_DIR.glob("*.json"):
        (external / seed.name).write_text(seed.read_text())
    code = main(
        [
            "run",
            "Add Patient Financial Class to AR Aging",
            "-o",
            str(tmp_path / "out"),
            "--metadata-dir",
            str(external),
        ]
    )
    assert code == EXIT_OK
