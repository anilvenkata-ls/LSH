"""Minimal PDF writer used for the validation report.

Supports the base-14 Helvetica fonts, headings, body text and monospaced blocks,
which is everything the validation report needs, with no dependencies.
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Iterable, Sequence

_PAGE_WIDTH = 612
_PAGE_HEIGHT = 792
_MARGIN = 54
_LEADING = 14

_STYLES = {
    "title": ("F2", 18, 22, 96),
    "h1": ("F2", 14, 18, 92),
    "h2": ("F2", 11, 16, 96),
    "body": ("F1", 10, 13, 104),
    "mono": ("F3", 8, 10, 118),
}


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _wrap(text: str, width: int) -> list[str]:
    if not text.strip():
        return [""]
    return textwrap.wrap(text, width=width) or [""]


def _content_stream(lines: Sequence[tuple[str, str]]) -> str:
    parts = ["BT"]
    y = _PAGE_HEIGHT - _MARGIN
    current_font = None
    for style, text in lines:
        font, size, leading, _ = _STYLES.get(style, _STYLES["body"])
        y -= leading
        if (font, size) != current_font:
            parts.append(f"/{font} {size} Tf")
            current_font = (font, size)
        parts.append(f"1 0 0 1 {_MARGIN} {y} Tm ({_escape(text)}) Tj")
    parts.append("ET")
    return "\n".join(parts)


def _paginate(lines: Sequence[tuple[str, str]]) -> list[list[tuple[str, str]]]:
    pages: list[list[tuple[str, str]]] = []
    current: list[tuple[str, str]] = []
    height = 0.0
    usable = _PAGE_HEIGHT - 2 * _MARGIN
    for style, text in lines:
        leading = _STYLES.get(style, _STYLES["body"])[2]
        if height + leading > usable and current:
            pages.append(current)
            current, height = [], 0.0
        current.append((style, text))
        height += leading
    if current:
        pages.append(current)
    return pages or [[("body", "")]]


def write_pdf(path: str | Path, blocks: Iterable[tuple[str, str]]) -> Path:
    """Write ``blocks`` of ``(style, text)`` pairs to a PDF file."""

    wrapped: list[tuple[str, str]] = []
    for style, text in blocks:
        width = _STYLES.get(style, _STYLES["body"])[3]
        for line in text.splitlines() or [""]:
            wrapped.extend((style, chunk) for chunk in _wrap(line, width))

    pages = _paginate(wrapped)
    objects: list[str] = []

    font_ids = {"F1": "Helvetica", "F2": "Helvetica-Bold", "F3": "Courier"}
    first_page_obj = 3 + len(font_ids)
    page_object_ids = [first_page_obj + 2 * i for i in range(len(pages))]

    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{pid} 0 R" for pid in page_object_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>")
    for name, base_font in font_ids.items():
        objects.append(f"<< /Type /Font /Subtype /Type1 /BaseFont /{base_font} /Name /{name} >>")

    font_refs = " ".join(f"/{name} {3 + index} 0 R" for index, name in enumerate(font_ids))
    for index, page_lines in enumerate(pages):
        content = _content_stream(page_lines)
        content_id = page_object_ids[index] + 1
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {_PAGE_WIDTH} {_PAGE_HEIGHT}] "
            f"/Resources << /Font << {font_refs} >> >> /Contents {content_id} 0 R >>"
        )
        objects.append(f"<< /Length {len(content.encode('latin-1', 'replace'))} >>\nstream\n{content}\nendstream")

    body = "%PDF-1.4\n"
    offsets = [0]
    for number, payload in enumerate(objects, start=1):
        offsets.append(len(body.encode("latin-1", "replace")))
        body += f"{number} 0 obj\n{payload}\nendobj\n"

    xref_offset = len(body.encode("latin-1", "replace"))
    xref = [f"xref\n0 {len(objects) + 1}\n", "0000000000 65535 f \n"]
    xref += [f"{offset:010d} 00000 n \n" for offset in offsets[1:]]
    body += "".join(xref)
    body += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body.encode("latin-1", "replace"))
    return target


def markdown_to_blocks(markdown: str) -> list[tuple[str, str]]:
    """Convert the generated markdown reports into PDF blocks."""

    blocks: list[tuple[str, str]] = []
    in_code = False
    table: list[str] = []

    def flush_table() -> None:
        if table:
            blocks.extend(("mono", line) for line in _format_table(table))
            table.clear()

    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_table()
            in_code = not in_code
            continue
        if in_code:
            blocks.append(("mono", line))
            continue
        if stripped.startswith("|"):
            table.append(stripped)
            continue
        flush_table()
        if stripped.startswith("# "):
            blocks.append(("title", stripped[2:]))
        elif stripped.startswith("## "):
            blocks.append(("h1", stripped[3:]))
        elif stripped.startswith("### "):
            blocks.append(("h2", stripped[4:]))
        else:
            blocks.append(("body", stripped.replace("**", "").replace("`", "")))
    flush_table()
    return blocks


def _format_table(rows: Sequence[str]) -> list[str]:
    """Render a markdown table as aligned monospaced text."""

    parsed = [
        [cell.strip().replace("**", "").replace("`", "") for cell in row.strip().strip("|").split("|")]
        for row in rows
        if set(row.replace("|", "").replace("-", "").replace(":", "").strip()) != set()
        or row.strip("|- :") != ""
    ]
    parsed = [cells for cells in parsed if not all(set(cell) <= {"-", ":", " "} for cell in cells)]
    if not parsed:
        return []
    width = max(len(cells) for cells in parsed)
    parsed = [cells + [""] * (width - len(cells)) for cells in parsed]
    widths = _allocate_widths([max(len(cells[i]) for cells in parsed) for i in range(width)])
    lines = []
    for index, cells in enumerate(parsed):
        rendered = "   ".join(
            (cell if len(cell) <= widths[i] else cell[: max(1, widths[i] - 1)] + "~").ljust(widths[i])
            for i, cell in enumerate(cells)
        )
        lines.append(rendered.rstrip())
        if index == 0:
            lines.append("   ".join("-" * w for w in widths))
    return lines


def _allocate_widths(natural: list[int], minimum: int = 6) -> list[int]:
    """Shrink the widest columns first until the row fits the page."""

    budget = _STYLES["mono"][3] - 3 * (len(natural) - 1)
    widths = list(natural)
    while sum(widths) > budget:
        widest = max(range(len(widths)), key=lambda i: widths[i])
        if widths[widest] <= minimum:
            break
        widths[widest] -= 1
    return widths
