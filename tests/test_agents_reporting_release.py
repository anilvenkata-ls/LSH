from __future__ import annotations

from rcm_change_platform.agents import (
    DeploymentReadinessAgent,
    DocumentationAgent,
    ImpactAnalysisAgent,
    IntegrationTestingAgent,
    MetadataDiscoveryAgent,
    PowerBIImpactAgent,
    RequestIntakeAgent,
    SqlChangeGenerationAgent,
    UnitTestGenerationAgent,
)
from rcm_change_platform.models import TestStatus as Status

THROUGH_POWER_BI = (
    RequestIntakeAgent,
    MetadataDiscoveryAgent,
    ImpactAnalysisAgent,
    SqlChangeGenerationAgent,
    DocumentationAgent,
    UnitTestGenerationAgent,
    IntegrationTestingAgent,
    PowerBIImpactAgent,
)
THROUGH_READINESS = THROUGH_POWER_BI + (DeploymentReadinessAgent,)


def test_power_bi_plan_targets_the_dataset_table_fed_by_the_modified_view(run_agents):
    context = run_agents(THROUGH_POWER_BI)
    plan = context.power_bi
    assert plan.dataset == "pb_ar_aging"
    assert plan.workspace == "RCM Analytics"
    assert plan.refresh_required
    add_column = [change for change in plan.changes if change.action == "Add column"]
    assert len(add_column) == 1
    assert add_column[0].target == "pb_ar_aging.AR Detail"


def test_power_bi_plan_lists_measures_relationships_and_visuals(run_agents):
    context = run_agents(THROUGH_POWER_BI)
    plan = context.power_bi
    assert "Total AR Balance" in plan.impacted_measures
    assert "AR Over 90 Pct" in plan.impacted_measures
    assert any("AR Detail[aging_bucket]" in rel for rel in plan.impacted_relationships)
    assert any("Payer Analysis" in visual for visual in plan.impacted_visuals)
    assert any(change.action == "Publish validation" for change in plan.changes)


def test_power_bi_tmdl_snippet_maps_the_data_type(run_agents):
    context = run_agents(THROUGH_POWER_BI)
    snippet = context.power_bi.tmdl_snippet
    assert "column patient_financial_class" in snippet
    assert "dataType: string" in snippet
    assert "summarizeBy: none" in snippet


def test_power_bi_warns_when_no_dataset_table_is_affected(run_agents, make_repo):
    def repoint_dataset(payload):
        for dataset in payload["power_bi"]["datasets"]:
            if dataset["name"] == "pb_ar_aging":
                for table in dataset["tables"]:
                    if table["name"] == "AR Detail":
                        table["source"] = "rcm.vw_ar_aging_summary"

    context = run_agents(THROUGH_POWER_BI, repo=make_repo(repoint_dataset))
    assert any("manual query change" in warning for warning in context.warnings)


def test_checklist_is_complete_for_a_clean_change(run_agents):
    context = run_agents(THROUGH_READINESS)
    checklist = context.checklist
    assert checklist.ready
    assert checklist.blockers == []
    outstanding = [item.item for item in checklist.items if not item.complete]
    assert outstanding == ["Report visuals reviewed by a human"]
    assert checklist.sections() == ["Development", "Testing", "Reporting", "Documentation", "Governance"]


def test_checklist_blocks_when_a_unit_test_fails(run_agents):
    context = run_agents(THROUGH_POWER_BI)
    context.unit_run.results[0].status = Status.FAILED
    DeploymentReadinessAgent().run(context)
    assert not context.checklist.ready
    assert any("Unit tests passed" in blocker for blocker in context.checklist.blockers)


def test_checklist_blocks_on_unexecuted_tests(run_agents):
    context = run_agents(THROUGH_READINESS, execute_tests=False)
    assert not context.checklist.ready
    blockers = " ".join(context.checklist.blockers)
    assert "Unit tests passed" in blockers and "Integration tests passed" in blockers


def test_checklist_blocks_on_pii_columns(run_agents):
    context = run_agents(THROUGH_READINESS, "Add Patient State to the AR Aging Report")
    assert any("PII review" in blocker for blocker in context.checklist.blockers)


def test_documentation_agent_drafts_every_document(run_agents):
    context = run_agents(THROUGH_POWER_BI)
    assert set(context.documents) == {
        "Requirement.md",
        "Technical_Design.md",
        "PR_Description.md",
        "Release_Notes.md",
        "Validation_Report.md",
    }
    design = context.documents["Technical_Design.md"]
    assert "## 4. Impacted Objects" in design
    assert "rcm.sp_load_ar_fact" in design
    assert "## 9. Rollback Strategy" in design
