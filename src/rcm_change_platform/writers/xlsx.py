"""Minimal XLSX writer.

The impact matrix ships as a spreadsheet because that is what reviewers pass
around. Writing the handful of OOXML parts directly keeps the platform free of
third party dependencies.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any, Sequence

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
{sheet_overrides}
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>
"""

_ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
"""

_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><name val="Calibri"/></font>
    <font><b/><sz val="11"/><name val="Calibri"/></font>
  </fonts>
  <fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="2">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>
"""


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _column_letter(index: int) -> str:
    letters = ""
    while index >= 0:
        letters = chr(ord("A") + index % 26) + letters
        index = index // 26 - 1
    return letters


def _cell_xml(reference: str, value: Any, header: bool) -> str:
    style = ' s="1"' if header else ""
    if isinstance(value, bool) or value is None:
        value = "" if value is None else str(value)
    if isinstance(value, (int, float)):
        return f'<c r="{reference}"{style}><v>{value}</v></c>'
    text = _escape(str(value))
    return f'<c r="{reference}" t="inlineStr"{style}><is><t xml:space="preserve">{text}</t></is></c>'


def _sheet_xml(rows: Sequence[Sequence[Any]], header_row: bool = True) -> str:
    body = []
    for row_index, row in enumerate(rows, start=1):
        cells = "".join(
            _cell_xml(f"{_column_letter(col_index)}{row_index}", value, header_row and row_index == 1)
            for col_index, value in enumerate(row)
        )
        body.append(f'<row r="{row_index}">{cells}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(body)}</sheetData></worksheet>"
    )


def write_xlsx(path: str | Path, sheets: dict[str, Sequence[Sequence[Any]]]) -> Path:
    """Write ``sheets`` (name -> rows) as a minimal but valid xlsx workbook."""

    if not sheets:
        raise ValueError("At least one sheet is required")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    names = list(sheets)
    overrides = "\n".join(
        f'  <Override PartName="/xl/worksheets/sheet{i}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, len(names) + 1)
    )
    workbook_sheets = "".join(
        f'<sheet name="{_escape(name[:31])}" sheetId="{i}" r:id="rId{i}"/>'
        for i, name in enumerate(names, start=1)
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{workbook_sheets}</sheets></workbook>"
    )
    relationships = "".join(
        f'<Relationship Id="rId{i}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, len(names) + 1)
    )
    relationships += (
        f'<Relationship Id="rId{len(names) + 1}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{relationships}</Relationships>"
    )

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES.format(sheet_overrides=overrides))
        archive.writestr("_rels/.rels", _ROOT_RELS)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/styles.xml", _STYLES)
        for index, name in enumerate(names, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _sheet_xml(sheets[name]))
    return target
