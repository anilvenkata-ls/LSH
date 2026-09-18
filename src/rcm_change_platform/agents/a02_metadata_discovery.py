"""Agent 2 - Metadata Discovery.

Resolves the business phrase to a physical column by consulting, in order: the
certified data dictionary, the information schema, the lineage repository, Jira
history and existing documentation. The result is a metadata document with the
evidence trail that later agents (and reviewers) rely on.
"""

from __future__ import annotations

from ..context import ChangeContext
from ..llm import complete_json
from ..models import ColumnMetadata, MetadataDocument, MetadataEvidence
from .base import Agent

_DIRECT_MATCH_THRESHOLD = 0.62


class MetadataDiscoveryAgent(Agent):
    name = "metadata_discovery"
    step = 2

    def execute(self, context: ChangeContext) -> str:
        request = context.request
        if request is None:
            context.halt(self.name, "No structured request available.")
            return "missing request"

        phrase = request.requested_column
        evidence: list[MetadataEvidence] = []
        column, candidates = self._resolve_column(context, phrase, evidence)

        document = MetadataDocument(column=column, candidates=candidates, evidence=evidence)

        if column is None:
            options = ", ".join(f"{c.physical_table}.{c.physical_column} ({c.match_score:.2f})" for c in candidates[:3])
            document.unresolved_reason = (
                f"'{phrase}' could not be resolved to a certified column. Closest candidates: {options or 'none'}."
            )
            context.metadata = document
            context.halt(self.name, document.unresolved_reason)
            return document.unresolved_reason

        document.upstream_dependencies = self._upstream(context, column.physical_table, evidence)
        document.related_tickets = self._tickets(context, column.physical_table, request.report, evidence)
        document.related_documents = self._documents(context, column.physical_table, request.report, evidence)

        context.metadata = document
        if not column.certified:
            context.warn(
                f"{column.physical_table}.{column.physical_column} is not certified in the data dictionary; "
                "confirm the definition with the data steward."
            )
        if column.pii:
            context.warn(
                f"{column.physical_table}.{column.physical_column} is flagged as PII; "
                "confirm the report audience is approved to see it."
            )
        return (
            f"resolved to {column.physical_table}.{column.physical_column} "
            f"{column.data_type} via {column.matched_on} (score {column.match_score:.2f})"
        )

    # -- resolution ----------------------------------------------------
    def _resolve_column(
        self, context: ChangeContext, phrase: str, evidence: list[MetadataEvidence]
    ) -> tuple[ColumnMetadata | None, list[ColumnMetadata]]:
        repo = context.repo
        candidates: list[ColumnMetadata] = []

        term, score, _ = repo.find_term(phrase)
        evidence.append(
            MetadataEvidence(
                source="Data Dictionary",
                reference=term["business_term"] if term else "no match",
                detail=f"fuzzy match score {score:.2f} for '{phrase}'",
            )
        )

        if term:
            column = self._from_term(repo, term, score)
            if column:
                evidence.append(
                    MetadataEvidence(
                        source="Information Schema",
                        reference=f"{column.physical_table}.{column.physical_column}",
                        detail=f"{column.data_type}, nullable={column.nullable}",
                    )
                )
                return column, [column]
            context.warn(
                f"Data dictionary term '{term['business_term']}' points at "
                f"{term.get('physical_table')}.{term.get('physical_column')} which is missing from the "
                "information schema; falling back to a physical column search."
            )

        physical = repo.find_physical_columns(phrase)
        for candidate, candidate_score in physical:
            candidates.append(
                ColumnMetadata(
                    business_term=candidate.name.replace("_", " ").title(),
                    physical_table=candidate.table,
                    physical_column=candidate.name,
                    data_type=candidate.data_type,
                    definition=candidate.description,
                    nullable=candidate.nullable,
                    match_score=candidate_score,
                    matched_on="information_schema",
                )
            )
        evidence.append(
            MetadataEvidence(
                source="Information Schema",
                reference=candidates[0].physical_column if candidates else "no match",
                detail=f"best physical column score {candidates[0].match_score:.2f}" if candidates else "no candidates",
            )
        )

        chosen = self._disambiguate(context, phrase, candidates)
        if chosen and chosen.match_score >= _DIRECT_MATCH_THRESHOLD:
            return chosen, candidates
        return None, candidates

    @staticmethod
    def _from_term(repo, term: dict, score: float) -> ColumnMetadata | None:
        table = term.get("physical_table", "")
        column_name = term.get("physical_column", "")
        physical = repo.column(table, column_name)
        if physical is None:
            return None
        return ColumnMetadata(
            business_term=term["business_term"],
            physical_table=table,
            physical_column=column_name,
            data_type=physical.data_type or term.get("data_type", ""),
            definition=term.get("definition", physical.description),
            nullable=physical.nullable,
            domain_values=list(term.get("domain_values", [])),
            steward=term.get("steward", ""),
            pii=bool(term.get("pii", False)),
            certified=bool(term.get("certified", False)),
            match_score=round(score, 4),
            matched_on="data_dictionary",
        )

    def _disambiguate(
        self, context: ChangeContext, phrase: str, candidates: list[ColumnMetadata]
    ) -> ColumnMetadata | None:
        if not candidates:
            return None
        top = candidates[0]
        contenders = [c for c in candidates if abs(c.match_score - top.match_score) < 0.05]
        if len(contenders) > 1 and context.llm.available():
            payload = complete_json(
                context.llm,
                "Pick the physical column that best matches the business phrase.\n"
                f"Phrase: {phrase}\n"
                "Candidates:\n"
                + "\n".join(f"- {c.physical_table}.{c.physical_column}: {c.definition}" for c in contenders)
                + '\nReturn JSON: {"table": "...", "column": "..."}',
            )
            if payload:
                for candidate in contenders:
                    if (
                        candidate.physical_table == payload.get("table")
                        and candidate.physical_column == payload.get("column")
                    ):
                        candidate.matched_on = f"llm:{getattr(context.llm, 'name', 'unknown')}"
                        return candidate
        return top

    # -- context gathering ----------------------------------------------
    def _upstream(self, context: ChangeContext, table: str, evidence: list[MetadataEvidence]) -> list[str]:
        upstream = context.graph.upstream(table)
        evidence.append(
            MetadataEvidence(
                source="Column Lineage Repository",
                reference=table,
                detail=f"upstream producers: {', '.join(upstream) if upstream else 'none recorded'}",
            )
        )
        return upstream

    def _tickets(self, context: ChangeContext, table: str, report: str, evidence: list[MetadataEvidence]) -> list[dict]:
        tickets = context.repo.tickets_mentioning({table, report})
        evidence.append(
            MetadataEvidence(
                source="Jira",
                reference=", ".join(t["key"] for t in tickets) or "no related tickets",
                detail=f"history for {table} and {report}",
            )
        )
        return tickets

    def _documents(self, context: ChangeContext, table: str, report: str, evidence: list[MetadataEvidence]) -> list[dict]:
        documents = context.repo.documents_mentioning({table, report})
        evidence.append(
            MetadataEvidence(
                source="Existing Documentation",
                reference=", ".join(d["path"] for d in documents) or "no related documents",
                detail=f"documents referencing {table} or {report}",
            )
        )
        return documents
