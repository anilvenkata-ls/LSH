from __future__ import annotations

import pytest

from rcm_change_platform.agents import MetadataDiscoveryAgent, RequestIntakeAgent
from rcm_change_platform.models import ChangeType

INTAKE = (RequestIntakeAgent,)
INTAKE_AND_METADATA = (RequestIntakeAgent, MetadataDiscoveryAgent)


@pytest.mark.parametrize(
    "phrase",
    [
        "Add Patient Financial Class to the AR Aging Report",
        'Add "Patient Financial Class" column to the AR Aging Report',
        "Please add the patient financial class field to AR Aging",
        "Include Patient Financial Class on the accounts receivable aging dashboard",
        "The AR Aging Report needs a Patient Financial Class column",
    ],
)
def test_intake_parses_common_request_shapes(run_agents, phrase):
    context = run_agents(INTAKE, phrase)
    assert not context.halted, context.warnings
    assert context.request.report == "AR Aging Report"
    assert context.request.requested_column.lower() == "patient financial class"
    assert context.request.change_type is ChangeType.ADD_COLUMN


def test_intake_extracts_the_business_reason(run_agents):
    context = run_agents(INTAKE, "Add Patient Financial Class to AR Aging because finance needs payer mix")
    assert context.request.business_reason == "finance needs payer mix"


def test_intake_assigns_a_stable_request_id(run_agents):
    first = run_agents(INTAKE, "Add Patient Financial Class to AR Aging")
    second = run_agents(INTAKE, "Add Patient Financial Class to AR Aging")
    assert first.request.request_id == second.request.request_id
    assert first.request.request_id.startswith("CR-")


def test_intake_halts_on_an_unknown_report(run_agents):
    context = run_agents(INTAKE, "Add Patient Financial Class to the Payroll Ledger Report")
    assert context.halted
    assert context.request.clarifications
    assert "Payroll Ledger" in context.request.clarifications[0]


def test_intake_halts_on_an_empty_request(run_agents):
    context = run_agents(INTAKE, "   ")
    assert context.halted_by == "request_intake"


def test_intake_records_the_options_business_reason(run_agents):
    context = run_agents(INTAKE, "Add Patient Financial Class to AR Aging", business_reason="Payer analysis")
    assert context.request.business_reason == "Payer analysis"


def test_metadata_resolves_through_the_data_dictionary(run_agents):
    context = run_agents(INTAKE_AND_METADATA)
    column = context.metadata.column
    assert column.physical_table == "rcm.dim_patient"
    assert column.physical_column == "patient_financial_class"
    assert column.data_type == "VARCHAR(50)"
    assert column.matched_on == "data_dictionary"
    assert column.certified and not column.pii
    assert column.domain_values


def test_metadata_records_evidence_from_every_source(run_agents):
    context = run_agents(INTAKE_AND_METADATA)
    sources = {evidence.source for evidence in context.metadata.evidence}
    assert sources == {
        "Data Dictionary",
        "Information Schema",
        "Column Lineage Repository",
        "Jira",
        "Existing Documentation",
    }


def test_metadata_links_related_history(run_agents):
    context = run_agents(INTAKE_AND_METADATA)
    keys = {ticket["key"] for ticket in context.metadata.related_tickets}
    assert {"RCM-1187", "RCM-1610"} <= keys
    assert context.metadata.upstream_dependencies == ["glue_patient_dim_load", "source.patient_master"]


def test_metadata_warns_about_pii_and_uncertified_columns(run_agents):
    context = run_agents(INTAKE_AND_METADATA, "Add Patient State to the AR Aging Report")
    assert context.metadata.column.physical_column == "patient_state"
    assert any("PII" in warning for warning in context.warnings)
    assert any("not certified" in warning for warning in context.warnings)


def test_metadata_halts_when_the_phrase_cannot_be_resolved(run_agents):
    context = run_agents(INTAKE_AND_METADATA, "Add Zodiac Sign to the AR Aging Report")
    assert context.halted_by == "metadata_discovery"
    assert "could not be resolved" in context.metadata.unresolved_reason
    assert context.metadata.candidates


def test_metadata_falls_back_to_the_information_schema(run_agents, make_repo):
    def drop_dictionary(payload):
        payload["data_dictionary"]["terms"] = []

    context = run_agents(INTAKE_AND_METADATA, repo=make_repo(drop_dictionary))
    assert context.metadata.column.matched_on == "information_schema"
    assert context.metadata.column.physical_column == "patient_financial_class"


def test_metadata_warns_when_the_dictionary_points_at_a_missing_column(run_agents, make_repo):
    def break_mapping(payload):
        for term in payload["data_dictionary"]["terms"]:
            if term["business_term"] == "Patient Financial Class":
                term["physical_column"] = "financial_class_missing"

    context = run_agents(INTAKE_AND_METADATA, repo=make_repo(break_mapping))
    assert any("missing from the information schema" in warning for warning in context.warnings)
    assert context.metadata.column.matched_on == "information_schema"
