import json
import zipfile
from pathlib import Path

import pytest

from pbi_schema_remap import Remapper, remap_path
from pbi_schema_remap.cli import main
from pbi_schema_remap.formats import UnsupportedFileError

FIXTURE = Path(__file__).parent / "fixtures" / "Collections"
REDSHIFT = 'AmazonRedshift.Database("host:5439", "rcm")'


def test_sql_server_navigation_keeps_table_name():
    m = 'Source = Sql.Database("s", "d"),\nt = Source{[Schema="dbo",Item="Claims"]}[Data]'
    out = Remapper().rewrite_m(m, "x")
    assert 'Source{[Schema="athena_integration",Item="Claims"]}[Data]' in out
    assert 'Sql.Database("s", "d")' in out


def test_redshift_navigation_renames_schema_step_only():
    m = (
        f"Source = {REDSHIFT},\n"
        'public = Source{[Name="public"]}[Data],\n'
        'claims = public{[Name="claims"]}[Data]'
    )
    out = Remapper().rewrite_m(m, "x")
    assert 'public = Source{[Name="athena_integration"]}[Data]' in out
    assert 'public{[Name="claims"]}[Data]' in out


def test_inline_redshift_navigation():
    m = f'{REDSHIFT}{{[Name="rcm",Kind="Schema"]}}[Data]{{[Name="claims"]}}[Data]'
    out = Remapper().rewrite_m(m, "x")
    assert '{[Name="athena_integration",Kind="Schema"]}[Data]{[Name="claims"]}' in out


def test_native_sql_references_rewritten():
    m = (
        f'Value.NativeQuery({REDSHIFT}, "SELECT EXTRACT(YEAR FROM a.d) FROM rcm.ar_aging a'
        '#(lf)JOIN rcm.""Payer Map"" p ON 1=1 LEFT JOIN [RCM].[dbo].[Payers] y ON 1=1", null)'
    )
    remapper = Remapper()
    out = remapper.rewrite_m(m, "x")
    assert "EXTRACT(YEAR FROM a.d)" in out
    assert "FROM athena_integration.ar_aging a" in out
    assert 'JOIN athena_integration.""Payer Map"" p' in out
    assert "JOIN athena_integration.Payers y" in out
    assert [c.kind for c in remapper.changes] == ["sql", "sql", "sql"]


def test_only_schema_filter():
    m = 'a{[Schema="dbo",Item="A"]}[Data], b{[Schema="stage",Item="B"]}[Data]'
    out = Remapper(only_schemas={"DBO"}).rewrite_m(m, "x")
    assert 'Schema="athena_integration",Item="A"' in out
    assert 'Schema="stage",Item="B"' in out


def test_already_target_is_not_reported():
    remapper = Remapper()
    remapper.rewrite_m('a{[Schema="athena_integration",Item="A"]}[Data]', "x")
    assert remapper.changes == []


def test_switch_connector_navigation():
    m = 'Source = Sql.Database("s", "d"),\nt = Source{[Schema="dbo",Item="FactClaims"]}[Data]'
    r = Remapper(redshift_server="host:5439", redshift_database="rcm", lowercase_tables=True)
    out = r.rewrite_m(m, "x")
    assert f"Source = {REDSHIFT}," in out
    assert 'Source{[Name="athena_integration"]}[Data]{[Name="factclaims"]}[Data]' in out


def test_switch_connector_native_query():
    m = 'Sql.Database("s", "d", [Query="SELECT * FROM [dbo].[Claims]", CommandTimeout=#duration(0,0,5,0)])'
    r = Remapper(redshift_server="host:5439", redshift_database="rcm")
    out = r.rewrite_m(m, "x")
    assert out == (
        f'Value.NativeQuery({REDSHIFT}, "SELECT * FROM athena_integration.Claims", '
        "null, [EnableFolding=true])"
    )
    assert any("CommandTimeout" in w for w in r.warnings)


def test_switch_requires_both_settings():
    with pytest.raises(ValueError):
        Remapper(redshift_server="host")


def test_pbip_folder_end_to_end(tmp_path):
    out = remap_path(FIXTURE / "Collections.pbip", tmp_path / "out", remapper := Remapper())
    tables = out / "Collections.SemanticModel" / "definition" / "tables"
    assert 'Schema="athena_integration",Item="Claims"' in (tables / "Claims.tmdl").read_text()
    assert 'Source{[Name="athena_integration"]}' in (tables / "Payers.tmdl").read_text()
    assert "FROM athena_integration.ar_aging" in (tables / "Aging.tmdl").read_text()
    assert (out / "Collections.pbip").exists()
    assert len(remapper.changes) == 4
    original = FIXTURE / "Collections.SemanticModel" / "definition" / "tables" / "Claims.tmdl"
    assert 'Schema="dbo"' in original.read_text()


def _model(expression):
    return {
        "name": "SemanticModel",
        "model": {
            "tables": [
                {
                    "name": "Claims",
                    "partitions": [{"name": "p", "source": {"type": "m", "expression": expression}}],
                },
                {
                    "name": "Legacy",
                    "partitions": [
                        {"name": "q", "source": {"type": "query", "query": "SELECT * FROM dbo.legacy"}}
                    ],
                },
            ]
        },
    }


def test_bim_with_line_list(tmp_path):
    src = tmp_path / "model.bim"
    src.write_text(json.dumps(_model(["let", '  t = S{[Schema="dbo",Item="Claims"]}[Data]', "in t"])))
    dst = remap_path(src, tmp_path / "out.bim", Remapper())
    tables = json.loads(dst.read_text())["model"]["tables"]
    assert tables[0]["partitions"][0]["source"]["expression"][1] == (
        '  t = S{[Schema="athena_integration",Item="Claims"]}[Data]'
    )
    assert tables[1]["partitions"][0]["source"]["query"] == "SELECT * FROM athena_integration.legacy"


def test_pbit_round_trip(tmp_path):
    src = tmp_path / "Report.pbit"
    schema = json.dumps(_model('let t = S{[Schema="dbo",Item="Claims"]}[Data] in t'))
    with zipfile.ZipFile(src, "w") as z:
        z.writestr("Version", "1.28".encode("utf-16-le"))
        z.writestr("DataModelSchema", schema.encode("utf-16-le"), compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("Report/Layout", b"{}")

    dst = remap_path(src, None, Remapper())
    assert dst.name == "Report_redshift.pbit"
    with zipfile.ZipFile(dst) as z:
        assert z.namelist() == ["Version", "DataModelSchema", "Report/Layout"]
        assert z.getinfo("DataModelSchema").compress_type == zipfile.ZIP_DEFLATED
        doc = json.loads(z.read("DataModelSchema").decode("utf-16-le"))
        assert z.read("Report/Layout") == b"{}"
    expr = doc["model"]["tables"][0]["partitions"][0]["source"]["expression"]
    assert 'Schema="athena_integration",Item="Claims"' in expr


def test_pbix_rejected(tmp_path):
    src = tmp_path / "Report.pbix"
    src.write_bytes(b"PK")
    with pytest.raises(UnsupportedFileError, match="pbip"):
        remap_path(src, None, Remapper())


def test_cli_dry_run(tmp_path, capsys):
    assert main([str(FIXTURE), "-o", str(tmp_path / "out"), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "4 reference(s) remapped to 'athena_integration'" in out
    assert not (tmp_path / "out").exists()
