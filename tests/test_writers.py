from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile

import pytest

from rcm_change_platform.writers import markdown_to_blocks, write_pdf, write_xlsx
from rcm_change_platform.writers.pdf import _allocate_widths, _format_table
from rcm_change_platform.writers.xlsx import _column_letter


def test_column_letters_roll_over():
    assert [_column_letter(i) for i in (0, 25, 26, 27)] == ["A", "Z", "AA", "AB"]


def test_xlsx_is_a_valid_package(tmp_path):
    path = write_xlsx(
        tmp_path / "book.xlsx",
        {"Impact Matrix": [["Object", "Impact"], ["rcm.fact_ar", "Modify"]], "Numbers": [["n"], [42], [3.5]]},
    )
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        assert {"[Content_Types].xml", "xl/workbook.xml", "xl/worksheets/sheet1.xml", "xl/worksheets/sheet2.xml"} <= names
        for name in names:
            ET.fromstring(archive.read(name))
        sheet = archive.read("xl/worksheets/sheet1.xml").decode()
        assert "rcm.fact_ar" in sheet
        assert archive.read("xl/worksheets/sheet2.xml").decode().count("<v>42</v>") == 1


def test_xlsx_escapes_markup(tmp_path):
    path = write_xlsx(tmp_path / "escaped.xlsx", {"S": [["a & b <c>"]]})
    with zipfile.ZipFile(path) as archive:
        sheet = archive.read("xl/worksheets/sheet1.xml").decode()
    assert "a &amp; b &lt;c&gt;" in sheet
    ET.fromstring(sheet)


def test_xlsx_requires_a_sheet(tmp_path):
    with pytest.raises(ValueError):
        write_xlsx(tmp_path / "empty.xlsx", {})


def test_pdf_structure_is_well_formed(tmp_path):
    path = write_pdf(tmp_path / "report.pdf", [("title", "Validation Report"), ("body", "All checks passed.")])
    raw = path.read_bytes()
    assert raw.startswith(b"%PDF-1.4")
    assert raw.rstrip().endswith(b"%%EOF")
    assert b"/Type /Catalog" in raw and b"/Type /Page" in raw
    start = int(raw.split(b"startxref")[1].split(b"%%EOF")[0].strip())
    assert raw[start : start + 4] == b"xref"


def test_pdf_paginates_long_documents(tmp_path):
    raw = write_pdf(tmp_path / "long.pdf", [("body", f"line {i}") for i in range(200)]).read_bytes()
    assert raw.count(b"/Type /Page /Parent") == 4
    assert b"/Count 4" in raw


def test_pdf_escapes_reserved_characters(tmp_path):
    path = write_pdf(tmp_path / "escaped.pdf", [("body", "balance (net) \\ total")])
    assert rb"balance \(net\) \\ total" in path.read_bytes()


def test_markdown_blocks_map_headings_and_code():
    blocks = markdown_to_blocks("# Title\n\n## Section\n\ntext\n\n```sql\nSELECT 1;\n```\n")
    assert ("title", "Title") in blocks
    assert ("h1", "Section") in blocks
    assert ("mono", "SELECT 1;") in blocks


def test_markdown_tables_become_aligned_columns():
    lines = _format_table(["| Metric | Result |", "| --- | --- |", "| balance | PASS |"])
    assert lines[0].startswith("Metric")
    assert set(lines[1]) <= {"-", " "}
    assert lines[2].startswith("balance")
    assert len({len(line.rstrip()) for line in lines}) <= 3


def test_wide_tables_shrink_the_widest_column_first():
    widths = _allocate_widths([90, 40, 5])
    assert sum(widths) <= 118 - 3 * 2
    assert widths[2] == 5
    assert widths[0] > 6
