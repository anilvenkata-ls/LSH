"""Pipeline orchestration.

Agents run in order and share the :class:`ChangeContext`. When an agent halts
the run - an ambiguous request, an unresolvable column, SQL that will not
execute - the orchestrator still produces the documentation and package so the
requester receives the clarification questions and the evidence gathered so far
instead of a silent failure.
"""

from __future__ import annotations

from pathlib import Path

from .agents import PIPELINE, Agent, DocumentationAgent, FinalOutputAgent
from .agents.a10_final_package import write_run_manifest
from .catalog import MetadataRepository
from .context import ChangeContext, RunOptions
from .llm import LLMClient, default_client

SALVAGE_AGENTS: tuple[type[Agent], ...] = (DocumentationAgent, FinalOutputAgent)


class ChangePipeline:
    def __init__(self, agents: tuple[type[Agent], ...] = PIPELINE, *, salvage: bool = True):
        self.agents = agents
        self.salvage = salvage

    def run(self, context: ChangeContext) -> ChangeContext:
        try:
            executed: list[type[Agent]] = []
            for agent_class in self.agents:
                agent_class().run(context)
                executed.append(agent_class)
                if context.halted:
                    break
            if context.halted and self.salvage:
                for agent_class in SALVAGE_AGENTS:
                    if agent_class in executed:
                        continue
                    agent_class().run(context)
            if context.package:
                write_run_manifest(context, Path(context.package.root))
        finally:
            context.release_resources()
        return context


def run_change_request(
    request: str,
    *,
    options: RunOptions | None = None,
    repo: MetadataRepository | None = None,
    llm: LLMClient | None = None,
    pipeline: ChangePipeline | None = None,
) -> ChangeContext:
    """Run the full pipeline for a natural language request."""

    context = ChangeContext.create(
        request,
        repo=repo,
        options=options or RunOptions(),
        llm=llm if llm is not None else default_client(),
    )
    return (pipeline or ChangePipeline()).run(context)
