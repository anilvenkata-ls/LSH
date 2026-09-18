"""The ten agents of the RCM change automation pipeline."""

from .a01_intake import RequestIntakeAgent
from .a02_metadata_discovery import MetadataDiscoveryAgent
from .a03_impact_analysis import ImpactAnalysisAgent
from .a04_sql_generation import SqlChangeGenerationAgent, deployment_script
from .a05_documentation import DocumentationAgent, refresh_documents
from .a06_unit_tests import UnitTestGenerationAgent
from .a07_integration_tests import IntegrationTestingAgent
from .a08_power_bi import PowerBIImpactAgent
from .a09_deployment_readiness import DeploymentReadinessAgent
from .a10_final_package import FinalOutputAgent
from .base import Agent

#: Execution order of the pipeline.
PIPELINE: tuple[type[Agent], ...] = (
    RequestIntakeAgent,
    MetadataDiscoveryAgent,
    ImpactAnalysisAgent,
    SqlChangeGenerationAgent,
    DocumentationAgent,
    UnitTestGenerationAgent,
    IntegrationTestingAgent,
    PowerBIImpactAgent,
    DeploymentReadinessAgent,
    FinalOutputAgent,
)

__all__ = [
    "Agent",
    "PIPELINE",
    "RequestIntakeAgent",
    "MetadataDiscoveryAgent",
    "ImpactAnalysisAgent",
    "SqlChangeGenerationAgent",
    "DocumentationAgent",
    "UnitTestGenerationAgent",
    "IntegrationTestingAgent",
    "PowerBIImpactAgent",
    "DeploymentReadinessAgent",
    "FinalOutputAgent",
    "deployment_script",
    "refresh_documents",
]
