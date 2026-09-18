"""Object level lineage graph assembled from the metadata repository.

Data edges describe how values physically flow (staging -> procedure -> fact ->
view -> dataset -> report). Control edges describe orchestration (a Step Function
invoking a Glue job, a Lambda calling a stored procedure) so the impact analyst
can flag components that must be redeployed even though no column flows through
them.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable

from .repository import MetadataRepository

DATA = "data"
CONTROL = "control"


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    kind: str
    reason: str


class LineageGraph:
    def __init__(self, edges: Iterable[Edge]):
        self._edges = list(edges)
        self._downstream: dict[str, list[Edge]] = {}
        self._upstream: dict[str, list[Edge]] = {}
        for edge in self._edges:
            self._downstream.setdefault(edge.source, []).append(edge)
            self._upstream.setdefault(edge.target, []).append(edge)

    @classmethod
    def build(cls, repo: MetadataRepository) -> "LineageGraph":
        edges: list[Edge] = []

        for routine in repo.routines:
            name = routine["name"]
            for source in routine.get("reads", []):
                edges.append(Edge(source, name, DATA, f"{name} reads {source}"))
            for target in routine.get("writes", []):
                edges.append(Edge(name, target, DATA, f"{name} writes {target}"))

        for view in repo.views:
            for source in view.get("depends_on", []):
                edges.append(Edge(source, view["name"], DATA, f"{view['name']} selects from {source}"))

        for flow in repo.dataflows:
            for source in flow.get("sources", []):
                edges.append(Edge(source, flow["name"], DATA, f"{flow['name']} stages {source}"))
            for consumer in flow.get("consumers", []):
                edges.append(Edge(flow["name"], consumer, DATA, f"{consumer} consumes {flow['name']}"))

        for dataset in repo.datasets:
            for source in dataset.get("sources", []):
                edges.append(Edge(source, dataset["name"], DATA, f"{dataset['name']} imports {source}"))

        for report in repo.reports:
            dataset = report.get("dataset")
            if dataset:
                edges.append(Edge(dataset, report["name"], DATA, f"{report['name']} renders {dataset}"))

        for component in repo.etl_components:
            name = component["name"]
            for source in component.get("reads", []):
                edges.append(Edge(source, name, DATA, f"{name} reads {source}"))
            for target in component.get("writes", []):
                edges.append(Edge(name, target, DATA, f"{name} writes {target}"))
            for routine_name in component.get("calls", []):
                edges.append(Edge(routine_name, name, CONTROL, f"{name} invokes {routine_name}"))
            for dataset_name in component.get("refreshes", []):
                edges.append(Edge(dataset_name, name, CONTROL, f"{name} refreshes {dataset_name}"))
            for child in component.get("orchestrates", []):
                edges.append(Edge(child, name, CONTROL, f"{name} orchestrates {child}"))

        return cls(edges)

    # -- inspection ---------------------------------------------------
    @property
    def edges(self) -> list[Edge]:
        return list(self._edges)

    def nodes(self) -> set[str]:
        return set(self._downstream) | set(self._upstream)

    def has(self, node: str) -> bool:
        return node in self._downstream or node in self._upstream

    def outgoing(self, node: str, kinds: tuple[str, ...] = (DATA,)) -> list[Edge]:
        return [e for e in self._downstream.get(node, []) if e.kind in kinds]

    def incoming(self, node: str, kinds: tuple[str, ...] = (DATA,)) -> list[Edge]:
        return [e for e in self._upstream.get(node, []) if e.kind in kinds]

    # -- traversal ----------------------------------------------------
    def _closure(self, start: str, forward: bool, kinds: tuple[str, ...]) -> list[str]:
        seen: set[str] = set()
        order: list[str] = []
        queue: deque[str] = deque([start])
        while queue:
            node = queue.popleft()
            edges = self.outgoing(node, kinds) if forward else self.incoming(node, kinds)
            for edge in edges:
                neighbour = edge.target if forward else edge.source
                if neighbour in seen:
                    continue
                seen.add(neighbour)
                order.append(neighbour)
                queue.append(neighbour)
        return order

    def downstream(self, node: str, kinds: tuple[str, ...] = (DATA,)) -> list[str]:
        return self._closure(node, forward=True, kinds=kinds)

    def upstream(self, node: str, kinds: tuple[str, ...] = (DATA,)) -> list[str]:
        return self._closure(node, forward=False, kinds=kinds)

    def shortest_path(self, source: str, target: str, kinds: tuple[str, ...] = (DATA,)) -> list[str]:
        if source == target:
            return [source]
        previous: dict[str, str] = {}
        queue: deque[str] = deque([source])
        seen = {source}
        while queue:
            node = queue.popleft()
            for edge in self.outgoing(node, kinds):
                if edge.target in seen:
                    continue
                seen.add(edge.target)
                previous[edge.target] = node
                if edge.target == target:
                    path = [target]
                    while path[-1] != source:
                        path.append(previous[path[-1]])
                    return list(reversed(path))
                queue.append(edge.target)
        return []

    def explain(self, source: str, target: str) -> str:
        edge = next(
            (e for e in self._downstream.get(source, []) if e.target == target),
            None,
        )
        return edge.reason if edge else ""
