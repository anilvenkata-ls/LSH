"""Agent 1 - Request Intake.

Turns a free form business request into a structured :class:`ChangeRequest`.
An LLM is used when configured; the regex grammar below covers the request
shapes seen in the RCM intake queue and keeps the pipeline deterministic when
no provider is available.
"""

from __future__ import annotations

import hashlib
import re

from ..context import ChangeContext
from ..llm import complete_json
from ..models import ChangeRequest, ChangeType
from ..text import title_case
from .base import Agent

_REQUEST_PATTERNS = [
    re.compile(
        r"\b(?P<verb>add|include|append|surface|expose|show)\b\s+(?:a\s+|an\s+|the\s+|new\s+)*"
        r"(?P<column>.+?)\s*(?:column|field|attribute)?\s+"
        r"\b(?:to|on|in|onto|within)\b\s+(?:the\s+)?(?P<report>.+?)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?P<report>.+?)\s+(?:needs|requires)\s+(?:a\s+|an\s+|the\s+)?(?P<column>.+?)\s*"
        r"(?:column|field|attribute)?$",
        re.IGNORECASE,
    ),
]

_REASON_PATTERNS = [
    re.compile(r"\b(?:because|since)\b\s+(?P<reason>.+)$", re.IGNORECASE),
    re.compile(r"\bso\s+(?:that\s+)?(?P<reason>.+)$", re.IGNORECASE),
    re.compile(r"\b(?:needed|required)\s+for\s+(?P<reason>.+)$", re.IGNORECASE),
    re.compile(r"\breason\s*[:\-]\s*(?P<reason>.+)$", re.IGNORECASE),
]

_QUOTED = re.compile(r"[\"'“”‘’]([^\"'“”‘’]{2,60})[\"'“”‘’]")

_TRAILING_NOISE = re.compile(
    r"\s*\b(report|dashboard|extract|dataset|page|view)\b\s*$", re.IGNORECASE
)

_LLM_SYSTEM = (
    "You extract structured change requests for a healthcare revenue cycle data "
    "warehouse. Reply with JSON only."
)


class RequestIntakeAgent(Agent):
    name = "request_intake"
    step = 1

    def execute(self, context: ChangeContext) -> str:
        raw = context.raw_request.strip()
        if not raw:
            context.halt(self.name, "Empty request: nothing to analyse.")
            return "no request supplied"

        parsed = self._parse_with_llm(context, raw) or self._parse_with_rules(raw)
        column = parsed["requested_column"]
        report_phrase = parsed["report"]

        request = ChangeRequest(
            raw_request=raw,
            report=report_phrase,
            requested_column=column,
            business_reason=context.options.business_reason or parsed.get("business_reason", ""),
            change_type=ChangeType(parsed.get("change_type", ChangeType.ADD_COLUMN.value)),
            requested_by=context.options.requested_by,
            confidence=float(parsed.get("confidence", 0.0)),
            parser=parsed.get("parser", "rule_based"),
        )
        request.request_id = context.options.request_id or self._request_id(raw)

        if not column or not report_phrase:
            request.clarifications.append(
                "Could not identify both the requested column and the target report. "
                'Use the form: Add "<column>" to the <report> report.'
            )
            context.request = request
            context.halt(self.name, request.clarifications[-1])
            return "unable to parse request"

        matched_report, score, scored = context.repo.find_report(report_phrase)
        if matched_report:
            request.report = matched_report["name"]
            request.confidence = round(max(request.confidence, score), 4)
        else:
            near = ", ".join(f"{name} ({value:.2f})" for name, value in scored[:3])
            request.clarifications.append(
                f"No report in the catalog matches '{report_phrase}'. Closest entries: {near or 'none'}."
            )
            context.request = request
            context.halt(self.name, request.clarifications[-1])
            return f"unknown report '{report_phrase}'"

        if request.change_type is ChangeType.UNKNOWN:
            request.clarifications.append(
                "Only column additions are automated today; the request was logged for manual triage."
            )
            context.request = request
            context.halt(self.name, request.clarifications[-1])
            return "unsupported change type"

        context.request = request
        return (
            f"parsed '{request.requested_column}' for report '{request.report}' "
            f"(confidence {request.confidence:.2f}, parser {request.parser})"
        )

    # -- parsing -------------------------------------------------------
    def _parse_with_llm(self, context: ChangeContext, raw: str) -> dict | None:
        report_names = [report["name"] for report in context.repo.reports]
        prompt = (
            "Extract the structured change request from the sentence below.\n"
            f"Known reports: {report_names}\n"
            "Return JSON with keys report, requested_column, business_reason, change_type "
            "(one of add_column, unknown).\n\n"
            f"Request: {raw}"
        )
        payload = complete_json(context.llm, prompt, system=_LLM_SYSTEM)
        if not payload:
            return None
        column = str(payload.get("requested_column", "")).strip()
        report = str(payload.get("report", "")).strip()
        if not column or not report:
            return None
        change_type = str(payload.get("change_type", "add_column")).strip().lower()
        if change_type not in {item.value for item in ChangeType}:
            change_type = ChangeType.ADD_COLUMN.value
        return {
            "requested_column": title_case(column),
            "report": report,
            "business_reason": str(payload.get("business_reason", "")).strip(),
            "change_type": change_type,
            "confidence": 0.9,
            "parser": f"llm:{getattr(context.llm, 'name', 'unknown')}",
        }

    def _parse_with_rules(self, raw: str) -> dict:
        sentence = raw.strip().rstrip(".")
        reason = ""
        for pattern in _REASON_PATTERNS:
            match = pattern.search(sentence)
            if match:
                reason = match.group("reason").strip().rstrip(".")
                sentence = sentence[: match.start()].strip().rstrip(",;")
                break

        quoted = _QUOTED.findall(raw)
        column = ""
        report = ""
        confidence = 0.0

        for pattern in _REQUEST_PATTERNS:
            match = pattern.search(sentence)
            if not match:
                continue
            column = self._clean_column(match.group("column"))
            report = self._clean_report(match.group("report"))
            confidence = 0.75 if quoted else 0.6
            break

        if quoted and not column:
            column = self._clean_column(quoted[0])
            confidence = 0.5
        if quoted:
            column = self._clean_column(quoted[0])

        change_type = ChangeType.ADD_COLUMN.value
        if column and report and not re.search(r"\b(add|include|append|surface|expose|show|needs|requires)\b", raw, re.IGNORECASE):
            change_type = ChangeType.UNKNOWN.value

        return {
            "requested_column": column,
            "report": report,
            "business_reason": reason,
            "change_type": change_type,
            "confidence": confidence,
            "parser": "rule_based",
        }

    @staticmethod
    def _clean_column(value: str) -> str:
        cleaned = value.strip().strip("\"'“”‘’ ,")
        cleaned = re.sub(r"^(a|an|the|new)\s+", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*\b(column|field|attribute)\b\s*$", "", cleaned, flags=re.IGNORECASE)
        return title_case(cleaned) if cleaned else ""

    @staticmethod
    def _clean_report(value: str) -> str:
        cleaned = value.strip().strip("\"'“”‘’ ,.")
        cleaned = re.sub(r"^(a|an|the)\s+", "", cleaned, flags=re.IGNORECASE)
        previous = None
        while previous != cleaned:
            previous = cleaned
            cleaned = _TRAILING_NOISE.sub("", cleaned).strip()
        return cleaned

    @staticmethod
    def _request_id(raw: str) -> str:
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
        return f"CR-{digest.upper()}"
