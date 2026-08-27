from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from .literals import literal_value


@dataclass(frozen=True)
class VisualRecord:
    page_name: str
    page_display_name: str
    visual_name: str
    visual_type: str | None
    title: str | None
    category_label: str | None
    hidden: bool
    path: Path
    document: dict[str, Any]
    page_document: dict[str, Any]


def report_definition_root(report_dir: Path) -> Path:
    definition = report_dir / "definition"
    if not definition.is_dir():
        raise FileNotFoundError(
            f"PBIR definition folder not found: {definition}. "
            "Export the report as a Power BI Project with the enhanced PBIR format."
        )
    return definition


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, document: dict[str, Any]) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def iter_visuals(report_dir: Path) -> Iterator[VisualRecord]:
    pages_dir = report_definition_root(report_dir) / "pages"
    if not pages_dir.is_dir():
        return
    for page_dir in sorted(path for path in pages_dir.iterdir() if path.is_dir()):
        page_file = page_dir / "page.json"
        if not page_file.exists():
            continue
        page_document = load_json(page_file)
        page_name = str(page_document.get("name") or page_dir.name)
        page_display_name = str(page_document.get("displayName") or page_name)
        visuals_dir = page_dir / "visuals"
        if not visuals_dir.is_dir():
            continue
        for visual_dir in sorted(path for path in visuals_dir.iterdir() if path.is_dir()):
            visual_file = visual_dir / "visual.json"
            if not visual_file.exists():
                continue
            document = load_json(visual_file)
            visual = document.get("visual") if isinstance(document.get("visual"), dict) else {}
            yield VisualRecord(
                page_name=page_name,
                page_display_name=page_display_name,
                visual_name=str(document.get("name") or visual_dir.name),
                visual_type=visual.get("visualType") if isinstance(visual, dict) else None,
                title=_vco_text(visual, "title"),
                category_label=_object_text(visual, "label"),
                hidden=bool(document.get("isHidden", False)),
                path=visual_file,
                document=document,
                page_document=page_document,
            )


def inventory_report(report_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for visual in iter_visuals(report_dir):
        rows.append(
            {
                "pageName": visual.page_name,
                "pageDisplayName": visual.page_display_name,
                "visualName": visual.visual_name,
                "visualType": visual.visual_type,
                "title": visual.title,
                "categoryLabel": visual.category_label,
                "hidden": visual.hidden,
                "path": str(visual.path),
            }
        )
    return rows


def _vco_text(visual: dict[str, Any], object_name: str) -> str | None:
    objects = visual.get("visualContainerObjects") if isinstance(visual, dict) else None
    return _first_text_property(objects, object_name)


def _object_text(visual: dict[str, Any], object_name: str) -> str | None:
    objects = visual.get("objects") if isinstance(visual, dict) else None
    return _first_text_property(objects, object_name)


def _first_text_property(objects: Any, object_name: str) -> str | None:
    if not isinstance(objects, dict):
        return None
    entries = objects.get(object_name)
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        properties = entry.get("properties")
        if not isinstance(properties, dict):
            continue
        text = properties.get("text")
        decoded = literal_value(text)
        if isinstance(decoded, str):
            return decoded
    return None
