"""Enterprise metadata repository.

The repository is the single façade the agents use to reach the data dictionary,
information schema, lineage, ETL inventory, Power BI metadata, Jira history and
existing documentation. Seed files ship with the package so the platform runs
end to end offline; point ``MetadataRepository.load`` at another directory to
plug in metadata exported from the real environment.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, Iterable

from ..text import best_match, similarity

SEEDS_DIR = Path(__file__).parent / "seeds"

_SEED_FILES = {
    "information_schema": "information_schema.json",
    "data_dictionary": "data_dictionary.json",
    "etl_components": "etl_components.json",
    "power_bi": "power_bi.json",
    "jira_tickets": "jira_tickets.json",
    "documentation": "documentation.json",
    "sample_data": "sample_data.json",
}


@dataclass(frozen=True)
class Column:
    table: str
    name: str
    data_type: str
    nullable: bool
    description: str


class MetadataRepository:
    def __init__(self, payload: dict[str, dict[str, Any]]):
        self._payload = payload

    # -- construction -------------------------------------------------
    @classmethod
    def load(cls, directory: str | Path | None = None) -> "MetadataRepository":
        base = Path(directory) if directory else SEEDS_DIR
        payload: dict[str, dict[str, Any]] = {}
        for key, filename in _SEED_FILES.items():
            path = base / filename
            if path.exists():
                payload[key] = json.loads(path.read_text(encoding="utf-8"))
            else:
                payload[key] = {}
        return cls(payload)

    # -- raw sections -------------------------------------------------
    @property
    def information_schema(self) -> dict[str, Any]:
        return self._payload.get("information_schema", {})

    @property
    def platform(self) -> str:
        return self.information_schema.get("platform", "redshift")

    @property
    def tables(self) -> list[dict[str, Any]]:
        return self.information_schema.get("tables", [])

    @property
    def views(self) -> list[dict[str, Any]]:
        return self.information_schema.get("views", [])

    @property
    def routines(self) -> list[dict[str, Any]]:
        return self.information_schema.get("routines", [])

    @property
    def relationships(self) -> list[dict[str, Any]]:
        return self.information_schema.get("relationships", [])

    @property
    def etl_components(self) -> list[dict[str, Any]]:
        return self._payload.get("etl_components", {}).get("components", [])

    @property
    def datasets(self) -> list[dict[str, Any]]:
        return self._payload.get("power_bi", {}).get("datasets", [])

    @property
    def reports(self) -> list[dict[str, Any]]:
        return self._payload.get("power_bi", {}).get("reports", [])

    @property
    def dataflows(self) -> list[dict[str, Any]]:
        return self._payload.get("power_bi", {}).get("dataflows", [])

    @property
    def terms(self) -> list[dict[str, Any]]:
        return self._payload.get("data_dictionary", {}).get("terms", [])

    @property
    def tickets(self) -> list[dict[str, Any]]:
        return self._payload.get("jira_tickets", {}).get("tickets", [])

    @property
    def documents(self) -> list[dict[str, Any]]:
        return self._payload.get("documentation", {}).get("documents", [])

    @property
    def sample_data(self) -> dict[str, list[dict[str, Any]]]:
        return self._payload.get("sample_data", {}).get("tables", {})

    # -- lookups ------------------------------------------------------
    @cached_property
    def _tables_by_name(self) -> dict[str, dict[str, Any]]:
        return {table["name"]: table for table in self.tables}

    @cached_property
    def _views_by_name(self) -> dict[str, dict[str, Any]]:
        return {view["name"]: view for view in self.views}

    @cached_property
    def _routines_by_name(self) -> dict[str, dict[str, Any]]:
        return {routine["name"]: routine for routine in self.routines}

    def table(self, name: str) -> dict[str, Any] | None:
        return self._tables_by_name.get(name)

    def view(self, name: str) -> dict[str, Any] | None:
        return self._views_by_name.get(name)

    def routine(self, name: str) -> dict[str, Any] | None:
        return self._routines_by_name.get(name)

    def dataset(self, name: str) -> dict[str, Any] | None:
        return next((d for d in self.datasets if d["name"] == name), None)

    def report(self, name: str) -> dict[str, Any] | None:
        return next((r for r in self.reports if r["name"] == name), None)

    def etl_component(self, name: str) -> dict[str, Any] | None:
        return next((c for c in self.etl_components if c["name"] == name), None)

    def columns(self, table_name: str) -> list[Column]:
        table = self.table(table_name)
        if not table:
            return []
        return [
            Column(
                table=table_name,
                name=col["name"],
                data_type=col["data_type"],
                nullable=bool(col.get("nullable", True)),
                description=col.get("description", ""),
            )
            for col in table.get("columns", [])
        ]

    def column(self, table_name: str, column_name: str) -> Column | None:
        target = column_name.lower()
        return next((c for c in self.columns(table_name) if c.name.lower() == target), None)

    def has_column(self, table_name: str, column_name: str) -> bool:
        return self.column(table_name, column_name) is not None

    def object_type(self, name: str) -> str:
        if name in self._tables_by_name:
            return self._tables_by_name[name].get("object_type", "table")
        if name in self._views_by_name:
            return "view"
        if name in self._routines_by_name:
            return "stored_procedure"
        component = self.etl_component(name)
        if component:
            return component.get("object_type", "etl_component")
        if self.dataset(name):
            return "dataset"
        if self.report(name):
            return "report"
        if any(flow["name"] == name for flow in self.dataflows):
            return "dataflow"
        return "unknown"

    def layer_of(self, name: str) -> str:
        table = self.table(name)
        if table:
            return table.get("layer", "warehouse")
        if self.view(name) or self.routine(name):
            return "warehouse"
        if self.etl_component(name):
            return "etl"
        if self.dataset(name) or self.report(name) or any(f["name"] == name for f in self.dataflows):
            return "reporting"
        return "unknown"

    # -- fuzzy search -------------------------------------------------
    def find_report(self, phrase: str) -> tuple[dict[str, Any] | None, float, list[tuple[str, float]]]:
        candidates = [
            (report["name"], [report["name"], *report.get("aliases", [])])
            for report in self.reports
        ]
        name, score, scored = best_match(phrase, candidates, threshold=0.4)
        return (self.report(name) if name else None), score, scored

    def find_term(self, phrase: str) -> tuple[dict[str, Any] | None, float, list[tuple[str, float]]]:
        candidates = [
            (term["business_term"], [term["business_term"], *term.get("synonyms", [])])
            for term in self.terms
        ]
        name, score, scored = best_match(phrase, candidates, threshold=0.5)
        term = next((t for t in self.terms if t["business_term"] == name), None)
        return term, score, scored

    def find_physical_columns(self, phrase: str, limit: int = 5) -> list[tuple[Column, float]]:
        """Fall back to the information schema when the dictionary has no entry."""

        scored: list[tuple[Column, float]] = []
        for table in self.tables:
            for column in self.columns(table["name"]):
                score = max(
                    similarity(phrase, column.name),
                    similarity(phrase, column.description) * 0.8,
                )
                scored.append((column, round(score, 4)))
        scored.sort(key=lambda item: -item[1])
        return scored[:limit]

    # -- graph oriented helpers ---------------------------------------
    def routines_writing(self, table_name: str) -> list[dict[str, Any]]:
        return [r for r in self.routines if table_name in r.get("writes", [])]

    def routines_reading(self, table_name: str) -> list[dict[str, Any]]:
        return [r for r in self.routines if table_name in r.get("reads", [])]

    def views_depending_on(self, object_name: str) -> list[dict[str, Any]]:
        return [v for v in self.views if object_name in v.get("depends_on", [])]

    def datasets_sourced_from(self, object_name: str) -> list[dict[str, Any]]:
        return [d for d in self.datasets if object_name in d.get("sources", [])]

    def dataflows_sourced_from(self, object_name: str) -> list[dict[str, Any]]:
        return [f for f in self.dataflows if object_name in f.get("sources", [])]

    def reports_for_dataset(self, dataset_name: str) -> list[dict[str, Any]]:
        return [r for r in self.reports if r.get("dataset") == dataset_name]

    def etl_components_touching(self, object_name: str) -> list[dict[str, Any]]:
        matches = []
        for component in self.etl_components:
            references = (
                component.get("reads", [])
                + component.get("writes", [])
                + component.get("calls", [])
                + component.get("refreshes", [])
                + component.get("orchestrates", [])
            )
            if object_name in references:
                matches.append(component)
        return matches

    def relationship_between(self, left: str, right: str) -> dict[str, Any] | None:
        for rel in self.relationships:
            if rel["from_table"] == left and rel["to_table"] == right:
                return rel
            if rel["from_table"] == right and rel["to_table"] == left:
                return rel
        return None

    def tickets_mentioning(self, objects: Iterable[str]) -> list[dict[str, Any]]:
        wanted = set(objects)
        return [t for t in self.tickets if wanted & set(t.get("objects", []))]

    def documents_mentioning(self, objects: Iterable[str]) -> list[dict[str, Any]]:
        wanted = set(objects)
        return [d for d in self.documents if wanted & set(d.get("objects", []))]
