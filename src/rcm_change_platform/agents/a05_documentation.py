"""Agent 5 - Documentation and GitOps.

Produces the technical design document, the requirement record and the pull
request description. The renderers are pure functions of the context, so the
final packaging agent re-renders them once test evidence exists; the documents
written here are what a reviewer would see if the run stopped early.
"""

from __future__ import annotations

from ..context import ChangeContext
from .. import rendering
from .base import Agent

DOCUMENT_BUILDERS = {
    "Requirement.md": rendering.requirement,
    "Technical_Design.md": rendering.technical_design,
    "PR_Description.md": rendering.pr_description,
    "Release_Notes.md": rendering.release_notes,
}


class DocumentationAgent(Agent):
    name = "documentation"
    step = 5

    def execute(self, context: ChangeContext) -> str:
        for filename, builder in DOCUMENT_BUILDERS.items():
            context.documents[filename] = builder(context)
        context.documents["Validation_Report.md"] = rendering.validation_report(context)
        return f"drafted {len(context.documents)} documents: {', '.join(context.documents)}"


def refresh_documents(context: ChangeContext) -> None:
    """Re-render every document so late evidence (tests, readiness) is included."""

    for filename, builder in DOCUMENT_BUILDERS.items():
        context.documents[filename] = builder(context)
    context.documents["Validation_Report.md"] = rendering.validation_report(context)
