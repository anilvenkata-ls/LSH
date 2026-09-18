from __future__ import annotations

from rcm_change_platform.catalog.lineage import CONTROL, DATA


def test_repository_exposes_every_seed_section(repo):
    assert repo.tables and repo.views and repo.routines
    assert repo.etl_components and repo.datasets and repo.reports
    assert repo.terms and repo.tickets and repo.documents
    assert repo.sample_data["rcm.dim_patient"]


def test_column_lookup_and_types(repo):
    column = repo.column("rcm.dim_patient", "patient_financial_class")
    assert column is not None
    assert column.data_type == "VARCHAR(50)"
    assert column.nullable is False
    assert repo.has_column("rcm.fact_ar", "balance")
    assert not repo.has_column("rcm.fact_ar", "patient_financial_class")


def test_object_type_and_layer_resolution(repo):
    assert repo.object_type("rcm.fact_ar") == "table"
    assert repo.object_type("rcm.vw_ar_detail") == "view"
    assert repo.object_type("rcm.sp_load_ar_fact") == "stored_procedure"
    assert repo.object_type("lambda_run_ar_load") == "lambda_function"
    assert repo.object_type("pb_ar_aging") == "dataset"
    assert repo.object_type("AR Aging Report") == "report"
    assert repo.layer_of("staging.stg_ar_transactions") == "staging"
    assert repo.layer_of("AR Aging Report") == "reporting"


def test_find_report_matches_alias_and_ignores_noise(repo):
    report, score, _ = repo.find_report("AR Aging")
    assert report is not None and report["name"] == "AR Aging Report"
    assert score > 0.9
    assert repo.find_report("accounts receivable aging")[0]["name"] == "AR Aging Report"
    assert repo.find_report("Payroll Ledger")[0] is None


def test_find_term_uses_synonyms(repo):
    term, score, _ = repo.find_term("fin class")
    assert term is not None and term["physical_column"] == "patient_financial_class"
    assert score >= 0.5


def test_find_physical_columns_ranks_by_similarity(repo):
    ranked = repo.find_physical_columns("aging bucket")
    assert ranked[0][0].name == "aging_bucket"
    assert ranked[0][1] > ranked[-1][1]


def test_graph_data_edges_follow_the_warehouse(graph):
    downstream = graph.downstream("rcm.fact_ar")
    assert "rcm.vw_ar_detail" in downstream
    assert "pb_ar_aging" in downstream
    assert "AR Aging Report" in downstream

    upstream = graph.upstream("AR Aging Report")
    assert {"rcm.fact_ar", "rcm.sp_load_ar_fact", "staging.stg_ar_transactions"} <= set(upstream)


def test_shortest_path_from_dimension_to_report(graph):
    path = graph.shortest_path("rcm.dim_patient", "AR Aging Report")
    assert path[0] == "rcm.dim_patient"
    assert path[-1] == "AR Aging Report"
    assert "pb_ar_aging" in path


def test_unrelated_objects_have_no_path(graph):
    assert graph.shortest_path("rcm.dim_provider", "AR Aging Report") == []


def test_control_edges_are_separate_from_data_edges(graph):
    data_only = graph.downstream("rcm.sp_load_ar_fact", kinds=(DATA,))
    with_control = graph.downstream("rcm.sp_load_ar_fact", kinds=(DATA, CONTROL))
    assert "lambda_run_ar_load" not in data_only
    assert "lambda_run_ar_load" in with_control
    assert "sfn_rcm_nightly" in with_control


def test_relationship_lookup_is_direction_agnostic(repo):
    left = repo.relationship_between("rcm.fact_ar", "rcm.dim_patient")
    right = repo.relationship_between("rcm.dim_patient", "rcm.fact_ar")
    assert left == right
    assert left["from_column"] == "patient_key"


def test_tickets_and_documents_are_matched_by_object(repo):
    tickets = repo.tickets_mentioning({"rcm.sp_load_ar_fact"})
    assert any(ticket["key"] == "RCM-1402" for ticket in tickets)
    documents = repo.documents_mentioning({"AR Aging Report"})
    assert any("ar_aging_report" in document["path"] for document in documents)
