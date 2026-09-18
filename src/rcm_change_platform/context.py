"""Shared state passed down the agent pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .catalog import LineageGraph, MetadataRepository
from .llm import LLMClient, NullLLM
from .models import (
    AgentReport,
    ChangePackage,
    ChangeRequest,
    DeploymentChecklist,
    ImpactMatrix,
    MetadataDocument,
    PowerBIPlan,
    ReconciliationReport,
    SqlChangeSet,
    TestRun,
    TestSuite,
)


@dataclass
class RunOptions:
    output_dir: Path = Path("out")
    execute_tests: bool = True
    requested_by: str = "business_user"
    business_reason: str = ""
    request_id: str = ""
    release: str = ""
    strict: bool = False

    def resolved_output(self) -> Path:
        return Path(self.output_dir)


@dataclass
class ChangeContext:
    raw_request: str
    repo: MetadataRepository
    graph: LineageGraph
    options: RunOptions = field(default_factory=RunOptions)
    llm: LLMClient = field(default_factory=NullLLM)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    request: ChangeRequest | None = None
    metadata: MetadataDocument | None = None
    impact: ImpactMatrix | None = None
    change_set: SqlChangeSet | None = None
    unit_suite: TestSuite | None = None
    integration_suite: TestSuite | None = None
    unit_run: TestRun | None = None
    integration_run: TestRun | None = None
    reconciliation: ReconciliationReport | None = None
    power_bi: PowerBIPlan | None = None
    checklist: DeploymentChecklist | None = None
    package: ChangePackage | None = None

    documents: dict[str, str] = field(default_factory=dict)
    reports: list[AgentReport] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    halted_by: str = ""
    #: Short lived resources shared between agents, e.g. warehouse sandboxes.
    scratch: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        raw_request: str,
        *,
        repo: MetadataRepository | None = None,
        options: RunOptions | None = None,
        llm: LLMClient | None = None,
    ) -> "ChangeContext":
        repository = repo or MetadataRepository.load()
        return cls(
            raw_request=raw_request,
            repo=repository,
            graph=LineageGraph.build(repository),
            options=options or RunOptions(),
            llm=llm or NullLLM(),
        )

    # -- helpers -------------------------------------------------------
    def warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    @property
    def halted(self) -> bool:
        return bool(self.halted_by)

    def halt(self, agent: str, reason: str) -> None:
        self.halted_by = agent
        self.warn(reason)

    def release_resources(self) -> None:
        """Close any sandbox connections opened during the run."""

        for value in self.scratch.values():
            close = getattr(value, "close", None)
            if callable(close):
                close()
        self.scratch.clear()

    def summary(self) -> dict[str, Any]:
        return {
            "request": self.request.to_dict() if self.request else None,
            "metadata_resolved": bool(self.metadata and self.metadata.resolved),
            "impacted_objects": self.impact.names() if self.impact else [],
            "unit_tests_passed": self.unit_run.passed if self.unit_run else None,
            "integration_tests_passed": self.integration_run.passed if self.integration_run else None,
            "reconciliation_balanced": self.reconciliation.balanced if self.reconciliation else None,
            "deployment_ready": self.checklist.ready if self.checklist else None,
            "package_root": self.package.root if self.package else None,
            "halted_by": self.halted_by,
            "warnings": list(self.warnings),
        }
