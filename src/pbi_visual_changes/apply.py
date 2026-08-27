from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from .inventory import VisualRecord, iter_visuals, write_json
from .literals import pbi_literal
from .models import (
    AppliedChange,
    ApplyResult,
    ChangeSpec,
    FileChange,
    SortChange,
    VisualChange,
    VisualMatch,
    VisualSet,
)


class ChangeApplyError(ValueError):
    """A visual change could not be applied safely."""


def load_change_spec(path: Path, repo_root: Path | None = None) -> ChangeSpec:
    payload = json.loads(path.read_text(encoding="utf-8"))
    root = repo_root or path.parent
    report = Path(payload["report"])
    if not report.is_absolute():
        report = (root / report).resolve()
    changes = tuple(_parse_change(item) for item in payload.get("changes") or [])
    if not changes:
        raise ChangeApplyError(f"Change spec has no changes: {path}")
    return ChangeSpec(report=report, ticket=str(payload.get("ticket") or ""), changes=changes)


def apply_change_spec(spec: ChangeSpec, *, dry_run: bool = False) -> ApplyResult:
    visuals = list(iter_visuals(spec.report))
    if not visuals:
        raise ChangeApplyError(f"No PBIR visuals found under {spec.report}")

    result = ApplyResult(dry_run=dry_run)
    documents: dict[Path, dict[str, Any]] = {}
    originals: dict[Path, dict[str, Any]] = {}

    for change in spec.changes:
        matches = [visual for visual in visuals if _matches(visual, change.match)]
        if len(matches) != 1:
            names = ", ".join(
                f"{item.page_display_name}/{item.visual_name}" for item in matches
            ) or "none"
            raise ChangeApplyError(
                f"Change '{change.id}' matched {len(matches)} visual(s): {names}. "
                "Each change must target exactly one visual."
            )
        visual = matches[0]
        if visual.path not in documents:
            originals[visual.path] = copy.deepcopy(visual.document)
            documents[visual.path] = copy.deepcopy(visual.document)
        _apply_set(documents[visual.path], change.set)
        result.applied.append(
            AppliedChange(
                change_id=change.id,
                visual_path=visual.path,
                page_name=visual.page_name,
                visual_name=visual.visual_name,
            )
        )

    for path, after in documents.items():
        before = originals[path]
        if before != after:
            result.files.append(FileChange(path=path, before=before, after=after))
            if not dry_run:
                write_json(path, after)
    return result


def _parse_change(item: dict[str, Any]) -> VisualChange:
    match_payload = item.get("match") or {}
    set_payload = item.get("set") or {}
    sort_payload = set_payload.get("sort")
    sort = None
    if sort_payload:
        sort = SortChange(
            query_ref=str(sort_payload["queryRef"]),
            direction=str(sort_payload.get("direction") or "Descending"),
        )
    change = VisualChange(
        id=str(item["id"]),
        description=str(item.get("description") or ""),
        match=VisualMatch(
            page_name=_optional_str(match_payload.get("pageName")),
            page_display_name=_optional_str(match_payload.get("pageDisplayName")),
            visual_name=_optional_str(match_payload.get("visualName")),
            visual_type=_optional_str(match_payload.get("visualType")),
            title=_optional_str(match_payload.get("title")),
            category_label=_optional_str(match_payload.get("categoryLabel")),
        ),
        set=VisualSet(
            title=_optional_str(set_payload.get("title")),
            title_show=set_payload.get("titleShow"),
            title_font_size=set_payload.get("titleFontSize"),
            category_label=_optional_str(set_payload.get("categoryLabel")),
            hidden=set_payload.get("hidden"),
            tab_order=set_payload.get("tabOrder"),
            sort=sort,
        ),
    )
    if change.match.is_empty():
        raise ChangeApplyError(f"Change '{change.id}' has an empty match block")
    if change.set.is_empty():
        raise ChangeApplyError(f"Change '{change.id}' has an empty set block")
    return change


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _matches(visual: VisualRecord, match: VisualMatch) -> bool:
    checks = [
        (match.page_name, visual.page_name),
        (match.page_display_name, visual.page_display_name),
        (match.visual_name, visual.visual_name),
        (match.visual_type, visual.visual_type),
        (match.title, visual.title),
        (match.category_label, visual.category_label),
    ]
    return all(expected is None or expected == actual for expected, actual in checks)


def _apply_set(document: dict[str, Any], settings: VisualSet) -> None:
    if settings.hidden is not None:
        if settings.hidden:
            document["isHidden"] = True
        else:
            document.pop("isHidden", None)
    if settings.tab_order is not None:
        position = document.setdefault("position", {})
        position["tabOrder"] = settings.tab_order

    visual = document.setdefault("visual", {})
    if not isinstance(visual, dict):
        raise ChangeApplyError("visual.json is missing a visual object")

    if any(value is not None for value in (settings.title, settings.title_show, settings.title_font_size)):
        vco = visual.setdefault("visualContainerObjects", {})
        title_entry = _ensure_object_entry(vco, "title")
        properties = title_entry.setdefault("properties", {})
        if settings.title_show is not None:
            properties["show"] = pbi_literal(settings.title_show)
        if settings.title is not None:
            properties["show"] = properties.get("show") or pbi_literal(True)
            properties["text"] = pbi_literal(settings.title)
        if settings.title_font_size is not None:
            properties["fontSize"] = pbi_literal(float(settings.title_font_size))

    if settings.category_label is not None:
        objects = visual.setdefault("objects", {})
        label_entry = _ensure_object_entry(objects, "label", selector={"id": "default"})
        properties = label_entry.setdefault("properties", {})
        properties["show"] = pbi_literal(True)
        properties["text"] = pbi_literal(settings.category_label)

    if settings.sort is not None:
        query = visual.setdefault("query", {})
        query["sortDefinition"] = [_sort_definition(settings.sort, visual)]


def _ensure_object_entry(
    container: dict[str, Any],
    name: str,
    *,
    selector: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entries = container.setdefault(name, [])
    if not isinstance(entries, list):
        raise ChangeApplyError(f"Expected {name} to be a list")
    if entries and isinstance(entries[0], dict):
        entry = entries[0]
    else:
        entry = {"properties": {}}
        entries.insert(0, entry)
    if selector is not None:
        entry.setdefault("selector", selector)
    return entry


def _sort_definition(sort: SortChange, visual: dict[str, Any]) -> dict[str, Any]:
    field = _existing_query_field(visual, sort.query_ref)
    if field is None:
        table, property_name = sort.query_ref.split(".", 1)
        field = {
            "Measure": {
                "Expression": {"SourceRef": {"Entity": table}},
                "Property": property_name,
            }
        }
    return {"direction": sort.direction, "field": copy.deepcopy(field)}


def _existing_query_field(visual: dict[str, Any], query_ref: str) -> dict[str, Any] | None:
    query_state = visual.get("query", {}).get("queryState")
    if not isinstance(query_state, dict):
        return None
    for payload in query_state.values():
        if not isinstance(payload, dict):
            continue
        projections = payload.get("projections")
        if not isinstance(projections, list):
            continue
        for projection in projections:
            if isinstance(projection, dict) and projection.get("queryRef") == query_ref:
                field = projection.get("field")
                if isinstance(field, dict):
                    return field
    return None


def snapshot_report_files(report_dir: Path) -> dict[Path, str]:
    """Capture every JSON file under a PBIR report for regression checks."""
    snapshot = {}
    for path in sorted(report_dir.rglob("*.json")):
        snapshot[path] = path.read_text(encoding="utf-8")
    return snapshot
