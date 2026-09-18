"""AI-powered RCM data engineering change automation platform.

Ten agents turn a natural language request such as "Add Patient Financial Class
to the AR Aging Report" into an impact analysis, generated SQL, executed tests,
a Power BI change plan, documentation and a deployment-ready change package.
"""

from .catalog import LineageGraph, MetadataRepository
from .context import ChangeContext, RunOptions
from .orchestrator import ChangePipeline, run_change_request

__version__ = "0.1.0"

__all__ = [
    "ChangeContext",
    "ChangePipeline",
    "LineageGraph",
    "MetadataRepository",
    "RunOptions",
    "run_change_request",
    "__version__",
]
