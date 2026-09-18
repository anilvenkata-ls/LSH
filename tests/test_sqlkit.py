from __future__ import annotations

import pytest

from rcm_change_platform import sqlkit

PROCEDURE = """CREATE OR REPLACE PROCEDURE rcm.sp_demo()
AS $$
BEGIN
    DELETE FROM rcm.fact_ar;

    INSERT INTO rcm.fact_ar (
        claim_id,
        balance
    )
    SELECT
        s.claim_id,
        CASE
            WHEN s.days <= 30 THEN '0-30'
            ELSE '30+'
        END
    FROM staging.stg_ar_transactions s
    JOIN rcm.dim_patient p ON p.patient_id = s.patient_id;
END;
$$ LANGUAGE plpgsql;"""

VIEW = """CREATE OR REPLACE VIEW rcm.vw_demo AS
SELECT
    f.claim_id,
    f.balance
FROM rcm.fact_ar f;"""


def test_projection_span_skips_case_blocks():
    start, end = sqlkit.projection_span(PROCEDURE)
    projection = PROCEDURE[start:end]
    assert "CASE" in projection
    assert "staging.stg_ar_transactions" not in projection


def test_split_projection_keeps_case_expression_intact():
    start, end = sqlkit.projection_span(PROCEDURE)
    items = sqlkit.split_projection(PROCEDURE[start:end])
    assert len(items) == 2
    assert "END" in items[1]


def test_add_projection_column_appends_with_indentation():
    updated = sqlkit.add_projection_column(VIEW, "f.patient_financial_class")
    assert "    f.balance,\n    f.patient_financial_class\nFROM rcm.fact_ar f;" in updated


def test_add_insert_column_extends_the_column_list():
    updated = sqlkit.add_insert_column(PROCEDURE, "patient_financial_class")
    assert "        balance,\n        patient_financial_class\n    )" in updated


def test_add_join_anchors_on_the_select_not_the_delete():
    clause = "LEFT JOIN rcm.dim_provider pr ON pr.provider_npi = s.provider_npi"
    updated = sqlkit.add_join(PROCEDURE, clause)
    lines = [line.strip() for line in updated.splitlines()]
    join_line = next(index for index, line in enumerate(lines) if line.startswith(clause))
    assert join_line == lines.index("JOIN rcm.dim_patient p ON p.patient_id = s.patient_id") + 1
    # the join must not leak into the CASE block or past the procedure terminator
    assert "END" not in updated.split(clause)[0].split("FROM staging")[-1]
    assert updated.index(clause) < updated.index("END;\n$$")


def test_add_join_keeps_the_statement_terminator_last():
    clause = "LEFT JOIN rcm.dim_provider pr ON pr.provider_npi = s.provider_npi"
    updated = sqlkit.add_join(PROCEDURE, clause)
    statement = [s for s in sqlkit.statements(sqlkit.procedure_body(updated)) if "INSERT" in s][0]
    assert statement.rstrip().endswith("s.provider_npi")


def test_alias_helpers():
    assert sqlkit.alias_for_table(PROCEDURE, "rcm.dim_patient") == "p"
    assert sqlkit.alias_for_table(PROCEDURE, "rcm.dim_payer") is None
    assert sqlkit.used_aliases(PROCEDURE) == {"s", "p"}
    assert sqlkit.suggest_alias(PROCEDURE, "rcm.dim_provider") == "p2"
    assert sqlkit.suggest_alias(PROCEDURE, "rcm.dim_payer") == "p2"


def test_statements_splits_on_top_level_semicolons():
    body = sqlkit.procedure_body(PROCEDURE)
    parts = sqlkit.statements(body)
    assert len(parts) == 2
    assert parts[0].startswith("DELETE FROM")
    assert parts[1].startswith("INSERT INTO")


def test_procedure_body_strips_the_wrapper():
    body = sqlkit.procedure_body(PROCEDURE)
    assert "CREATE OR REPLACE PROCEDURE" not in body
    assert "LANGUAGE plpgsql" not in body
    assert body.startswith("DELETE FROM")


def test_strip_comments_and_is_executable():
    script = "-- header\n-- more\nALTER TABLE t ADD COLUMN c INT;"
    assert sqlkit.strip_comments(script) == "ALTER TABLE t ADD COLUMN c INT;"
    assert sqlkit.is_executable(script)
    assert not sqlkit.is_executable("-- only a comment")


def test_references_table_ignores_partial_matches():
    assert sqlkit.references_table(VIEW, "rcm.fact_ar")
    assert not sqlkit.references_table(VIEW, "fact_ar_history")


def test_unified_diff_reports_the_added_line():
    updated = sqlkit.add_projection_column(VIEW, "f.new_column")
    diff = sqlkit.unified_diff(VIEW, updated, "vw_demo.sql")
    assert "+    f.new_column" in diff


def test_edit_errors_are_explicit():
    with pytest.raises(sqlkit.SqlEditError):
        sqlkit.projection_span("DELETE FROM rcm.fact_ar;")
    with pytest.raises(sqlkit.SqlEditError):
        sqlkit.add_insert_column("SELECT 1 FROM t", "c")
