"""Typed artifacts exchanged between the agents of the change automation pipeline.

Every agent consumes artifacts produced upstream and contributes new ones to the
:class:`ChangeContext`. Keeping the contracts explicit is what allows an agent to be
replaced by an LLM-backed implementation without touching the rest of the pipeline.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any


def _plain(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {k: _plain(v) for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


class Serializable:
    """Mixin adding a JSON friendly ``to_dict`` to the dataclass artifacts."""

    def to_dict(self) -> dict[str, Any]:
        return {k: _plain(v) for k, v in dataclasses.asdict(self).items()}  # type: ignore[call-overload]


class ChangeType(str, Enum):
    ADD_COLUMN = "add_column"
    UNKNOWN = "unknown"


class ImpactAction(str, Enum):
    MODIFY = "Modify"
    REFRESH = "Refresh"
    REDEPLOY = "Redeploy"
    REVIEW = "Review"
    NO_CHANGE = "No Change"


class Severity(str, Enum):
    BLOCKING = "blocking"
    WARNING = "warning"
    INFO = "info"


class TestStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Agent 1 - request intake
# ---------------------------------------------------------------------------


@dataclass
class ChangeRequest(Serializable):
    raw_request: str
    report: str
    requested_column: str
    business_reason: str = ""
    change_type: ChangeType = ChangeType.ADD_COLUMN
    requested_by: str = "business_user"
    confidence: float = 0.0
    clarifications: list[str] = field(default_factory=list)
    request_id: str = ""
    parser: str = "rule_based"


# ---------------------------------------------------------------------------
# Agent 2 - metadata discovery
# ---------------------------------------------------------------------------


@dataclass
class MetadataEvidence(Serializable):
    source: str
    reference: str
    detail: str


@dataclass
class ColumnMetadata(Serializable):
    business_term: str
    physical_table: str
    physical_column: str
    data_type: str
    definition: str
    nullable: bool = True
    domain_values: list[str] = field(default_factory=list)
    steward: str = ""
    pii: bool = False
    certified: bool = False
    match_score: float = 0.0
    matched_on: str = ""


@dataclass
class MetadataDocument(Serializable):
    column: ColumnMetadata | None
    upstream_dependencies: list[str] = field(default_factory=list)
    related_tickets: list[dict[str, Any]] = field(default_factory=list)
    related_documents: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[MetadataEvidence] = field(default_factory=list)
    candidates: list[ColumnMetadata] = field(default_factory=list)
    unresolved_reason: str = ""

    @property
    def resolved(self) -> bool:
        return self.column is not None


# ---------------------------------------------------------------------------
# Agent 3 - impact analysis
# ---------------------------------------------------------------------------


@dataclass
class ImpactItem(Serializable):
    object_name: str
    object_type: str
    action: ImpactAction
    layer: str
    rationale: str
    owner: str = ""
    risk: str = "low"


@dataclass
class ImpactMatrix(Serializable):
    items: list[ImpactItem] = field(default_factory=list)
    propagation_path: list[str] = field(default_factory=list)
    report: str = ""
    source_table: str = ""
    target_fact_table: str = ""
    join_plan: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def names(self) -> list[str]:
        return [item.object_name for item in self.items]


# ---------------------------------------------------------------------------
# Agent 4 - SQL change generation
# ---------------------------------------------------------------------------


@dataclass
class ObjectChange(Serializable):
    object_name: str
    object_type: str
    before: str
    after: str
    diff: str
    summary: str = ""


@dataclass
class SqlChangeSet(Serializable):
    migration_sql: str = ""
    rollback_sql: str = ""
    object_changes: list[ObjectChange] = field(default_factory=list)
    target_column: str = ""
    target_table: str = ""
    notes: list[str] = field(default_factory=list)

    def change_for(self, object_name: str) -> ObjectChange | None:
        for change in self.object_changes:
            if change.object_name == object_name:
                return change
        return None


# ---------------------------------------------------------------------------
# Agents 6 and 7 - test generation and execution
# ---------------------------------------------------------------------------


@dataclass
class TestCase(Serializable):
    name: str
    category: str
    sql: str
    expectation: str
    severity: Severity = Severity.BLOCKING
    assertion: dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSuite(Serializable):
    name: str
    description: str = ""
    cases: list[TestCase] = field(default_factory=list)

    def case(self, name: str) -> TestCase | None:
        for case in self.cases:
            if case.name == name:
                return case
        return None


@dataclass
class TestResult(Serializable):
    name: str
    category: str
    status: TestStatus
    expectation: str
    actual: str = ""
    message: str = ""
    severity: Severity = Severity.BLOCKING


@dataclass
class TestRun(Serializable):
    suite: str
    results: list[TestResult] = field(default_factory=list)
    executed: bool = True

    @property
    def passed(self) -> bool:
        return all(
            r.status is TestStatus.PASSED or r.severity is not Severity.BLOCKING
            for r in self.results
        )

    def count(self, status: TestStatus) -> int:
        return sum(1 for r in self.results if r.status is status)


@dataclass
class ReconciliationLine(Serializable):
    metric: str
    before: float
    after: float
    tolerance: float = 0.01

    @property
    def difference(self) -> float:
        return round(self.after - self.before, 6)

    @property
    def matched(self) -> bool:
        return abs(self.difference) <= self.tolerance


@dataclass
class ReconciliationReport(Serializable):
    lines: list[ReconciliationLine] = field(default_factory=list)
    executed: bool = True
    notes: list[str] = field(default_factory=list)

    @property
    def balanced(self) -> bool:
        return all(line.matched for line in self.lines)


# ---------------------------------------------------------------------------
# Agent 8 - Power BI
# ---------------------------------------------------------------------------


@dataclass
class PowerBIChange(Serializable):
    target: str
    target_type: str
    action: str
    detail: str


@dataclass
class PowerBIPlan(Serializable):
    dataset: str = ""
    report: str = ""
    workspace: str = ""
    changes: list[PowerBIChange] = field(default_factory=list)
    impacted_measures: list[str] = field(default_factory=list)
    impacted_relationships: list[str] = field(default_factory=list)
    impacted_visuals: list[str] = field(default_factory=list)
    refresh_required: bool = False
    tmdl_snippet: str = ""


# ---------------------------------------------------------------------------
# Agent 9 - deployment readiness
# ---------------------------------------------------------------------------


@dataclass
class ChecklistItem(Serializable):
    section: str
    item: str
    complete: bool
    detail: str = ""
    blocking: bool = True

    @property
    def marker(self) -> str:
        return "[x]" if self.complete else "[ ]"


@dataclass
class DeploymentChecklist(Serializable):
    items: list[ChecklistItem] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.blockers

    def sections(self) -> list[str]:
        seen: list[str] = []
        for item in self.items:
            if item.section not in seen:
                seen.append(item.section)
        return seen


# ---------------------------------------------------------------------------
# Agent 10 - final package
# ---------------------------------------------------------------------------


@dataclass
class ChangePackage(Serializable):
    root: str
    files: list[str] = field(default_factory=list)


@dataclass
class AgentReport(Serializable):
    agent: str
    step: int
    status: str
    summary: str
    duration_ms: float = 0.0
    warnings: list[str] = field(default_factory=list)
