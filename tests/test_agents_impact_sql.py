from __future__ import annotations

from rcm_change_platform.agents import (
    ImpactAnalysisAgent,
    MetadataDiscoveryAgent,
    RequestIntakeAgent,
    SqlChangeGenerationAgent,
    deployment_script,
)
from rcm_change_platform.models import ImpactAction

THROUGH_IMPACT = (RequestIntakeAgent, MetadataDiscoveryAgent, ImpactAnalysisAgent)
THROUGH_SQL = THROUGH_IMPACT + (SqlChangeGenerationAgent,)


def actions(context) -> dict[str, ImpactAction]:
    return {item.object_name: item.action for item in context.impact.items}


def test_impact_matrix_covers_warehouse_etl_and_reporting(run_agents):
    context = run_agents(THROUGH_IMPACT)
    result = actions(context)
    assert result["rcm.fact_ar"] is ImpactAction.MODIFY
    assert result["rcm.sp_load_ar_fact"] is ImpactAction.MODIFY
    assert result["rcm.vw_ar_detail"] is ImpactAction.MODIFY
    assert result["pb_ar_aging"] is ImpactAction.REFRESH
    assert result["df_rcm_ar"] is ImpactAction.REFRESH
    assert result["AR Aging Report"] is ImpactAction.MODIFY
    assert result["rcm.dim_patient"] is ImpactAction.NO_CHANGE
    assert result["lambda_run_ar_load"] is ImpactAction.REVIEW
    # control edges are followed transitively, so the orchestrator is listed too
    assert result["sfn_rcm_nightly"] is ImpactAction.REVIEW


def test_impact_leaves_unrelated_reports_alone(run_agents):
    context = run_agents(THROUGH_IMPACT)
    names = set(actions(context))
    assert "Denials Dashboard" not in names
    assert "pb_denials" not in names


def test_aggregate_views_are_flagged_rather_than_edited(run_agents):
    context = run_agents(THROUGH_IMPACT)
    assert actions(context)["rcm.vw_ar_aging_summary"] is ImpactAction.REVIEW
    assert any("grain" in warning for warning in context.impact.warnings)


def test_join_plan_detects_an_existing_join(run_agents):
    context = run_agents(THROUGH_IMPACT)
    plan = context.impact.join_plan
    assert plan["strategy"] == "existing_join"
    assert plan["expression"] == "p.patient_financial_class"


def test_join_plan_builds_a_new_join_when_needed(run_agents):
    context = run_agents(THROUGH_IMPACT, "Add Provider Specialty to the AR Aging Report")
    plan = context.impact.join_plan
    assert plan["strategy"] == "new_join"
    assert plan["join_to"] == "staging.stg_ar_transactions"
    assert plan["join_clause"].startswith("LEFT JOIN rcm.dim_provider")
    assert "provider_npi" in plan["join_clause"]


def test_unreachable_source_halts_the_run(run_agents, make_repo):
    def cut_relationships(payload):
        payload["information_schema"]["relationships"] = [
            rel
            for rel in payload["information_schema"]["relationships"]
            if rel["to_table"] != "rcm.dim_provider"
        ]

    context = run_agents(
        THROUGH_IMPACT,
        "Add Provider Specialty to the AR Aging Report",
        repo=make_repo(cut_relationships),
    )
    assert context.halted_by == "impact_analysis"
    assert "not joinable" in context.warnings[-1]


def test_propagation_path_follows_the_fact_load_not_the_shortest_route(run_agents):
    context = run_agents(THROUGH_IMPACT)
    assert context.impact.propagation_path == [
        "rcm.dim_patient",
        "rcm.sp_load_ar_fact",
        "rcm.fact_ar",
        "rcm.vw_ar_detail",
        "pb_ar_aging",
        "AR Aging Report",
    ]


def test_existing_column_is_reported_as_no_change(run_agents, make_repo):
    def preload_column(payload):
        for table in payload["information_schema"]["tables"]:
            if table["name"] == "rcm.fact_ar":
                table["columns"].append(
                    {
                        "name": "patient_financial_class",
                        "data_type": "VARCHAR(50)",
                        "nullable": True,
                        "description": "already present",
                    }
                )

    context = run_agents(THROUGH_SQL, repo=make_repo(preload_column))
    assert actions(context)["rcm.fact_ar"] is ImpactAction.NO_CHANGE
    assert context.change_set.migration_sql == ""
    assert any("already exists" in note for note in context.change_set.notes)


def test_generated_migration_and_rollback(run_agents):
    context = run_agents(THROUGH_SQL)
    change_set = context.change_set
    assert "ALTER TABLE rcm.fact_ar" in change_set.migration_sql
    assert "ADD COLUMN patient_financial_class VARCHAR(50)" in change_set.migration_sql
    assert "DROP COLUMN patient_financial_class" in change_set.rollback_sql
    assert "CREATE OR REPLACE PROCEDURE rcm.sp_load_ar_fact" in change_set.rollback_sql
    assert "patient_financial_class" not in change_set.rollback_sql.split("-- Restore view")[1].split("-- Restore stored")[0]


def test_procedure_edit_populates_insert_and_select(run_agents):
    context = run_agents(THROUGH_SQL)
    change = context.change_set.change_for("rcm.sp_load_ar_fact")
    assert change is not None
    added = [line for line in change.diff.splitlines() if line.startswith("+")]
    assert any("patient_financial_class" in line for line in added)
    assert change.after.count("patient_financial_class") == 2
    assert "p.patient_financial_class" in change.after


def test_view_edit_reads_from_the_fact_alias(run_agents):
    context = run_agents(THROUGH_SQL)
    change = context.change_set.change_for("rcm.vw_ar_detail")
    assert "f.patient_financial_class" in change.after
    assert change.summary == "selected f.patient_financial_class"


def test_new_join_is_added_once_to_the_procedure(run_agents):
    context = run_agents(THROUGH_SQL, "Add Provider Specialty to the AR Aging Report")
    change = context.change_set.change_for("rcm.sp_load_ar_fact")
    assert change.after.count("LEFT JOIN rcm.dim_provider") == 1
    assert change.after.index("LEFT JOIN rcm.dim_provider") > change.after.index("FROM staging.stg_ar_transactions")


def test_deployment_script_orders_migration_then_objects_then_reload(run_agents):
    context = run_agents(THROUGH_SQL)
    script = deployment_script(context)
    assert script.index("ALTER TABLE") < script.index("CREATE OR REPLACE PROCEDURE")
    assert script.index("CREATE OR REPLACE PROCEDURE") < script.index("CREATE OR REPLACE VIEW")
    assert script.rstrip().endswith("CALL rcm.sp_load_ar_fact();")
