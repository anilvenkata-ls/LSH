from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from rcm_change_platform.catalog import LineageGraph, MetadataRepository
from rcm_change_platform.catalog.repository import SEEDS_DIR, _SEED_FILES
from rcm_change_platform.context import ChangeContext, RunOptions
from rcm_change_platform.orchestrator import ChangePipeline

AR_REQUEST = "Add Patient Financial Class to the AR Aging Report"
PROVIDER_REQUEST = "Add Provider Specialty to the AR Aging Report"


def _seed_payload() -> dict:
    return {
        key: json.loads((SEEDS_DIR / filename).read_text(encoding="utf-8"))
        for key, filename in _SEED_FILES.items()
    }


@pytest.fixture(autouse=True)
def offline_llm(monkeypatch):
    """Keep every test hermetic, whatever the developer has exported."""

    for variable in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "RCM_LLM_MODEL"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("RCM_LLM_PROVIDER", "none")


@pytest.fixture
def seed_payload() -> dict:
    return _seed_payload()


@pytest.fixture
def repo() -> MetadataRepository:
    return MetadataRepository.load()


@pytest.fixture
def graph(repo: MetadataRepository) -> LineageGraph:
    return LineageGraph.build(repo)


@pytest.fixture
def make_repo():
    """Build a repository from the seeds with a mutation applied."""

    def factory(mutate=None) -> MetadataRepository:
        payload = copy.deepcopy(_seed_payload())
        if mutate:
            mutate(payload)
        return MetadataRepository(payload)

    return factory


@pytest.fixture
def make_context(tmp_path: Path):
    def factory(request: str = AR_REQUEST, *, repo: MetadataRepository | None = None, **options) -> ChangeContext:
        settings = {"output_dir": tmp_path / "artifacts", "execute_tests": True}
        settings.update(options)
        return ChangeContext.create(request, repo=repo, options=RunOptions(**settings))

    return factory


@pytest.fixture
def run_pipeline(make_context):
    def factory(request: str = AR_REQUEST, *, repo: MetadataRepository | None = None, **options) -> ChangeContext:
        context = make_context(request, repo=repo, **options)
        return ChangePipeline().run(context)

    return factory


@pytest.fixture
def run_agents(make_context):
    """Run a prefix of the pipeline, returning the context."""

    def factory(agents, request: str = AR_REQUEST, *, repo: MetadataRepository | None = None, **options) -> ChangeContext:
        context = make_context(request, repo=repo, **options)
        for agent_class in agents:
            agent_class().run(context)
            if context.halted:
                break
        return context

    return factory
