"""Agent base class shared by the ten pipeline stages."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

from ..context import ChangeContext
from ..models import AgentReport


class Agent(ABC):
    name: str = "agent"
    step: int = 0

    @abstractmethod
    def execute(self, context: ChangeContext) -> str:
        """Do the work and return a one line summary for the run report."""

    def run(self, context: ChangeContext) -> AgentReport:
        start = time.perf_counter()
        warnings_before = len(context.warnings)
        try:
            summary = self.execute(context)
            status = "halted" if context.halted_by == self.name else "completed"
        except Exception as exc:  # noqa: BLE001 - surfaced in the run report
            context.halt(self.name, f"{self.name} failed: {exc}")
            summary = f"failed: {exc}"
            status = "failed"
        report = AgentReport(
            agent=self.name,
            step=self.step,
            status=status,
            summary=summary,
            duration_ms=round((time.perf_counter() - start) * 1000, 3),
            warnings=context.warnings[warnings_before:],
        )
        context.reports.append(report)
        return report
