from __future__ import annotations

from typing import Any


def pbi_literal(value: Any) -> dict[str, Any]:
    """Encode a Python value as a Power BI PBIR literal expression."""
    if isinstance(value, bool):
        return {"expr": {"Literal": {"Value": "true" if value else "false"}}}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"expr": {"Literal": {"Value": f"{value}L"}}}
    if isinstance(value, float):
        as_int = int(value)
        if as_int == value:
            return {"expr": {"Literal": {"Value": f"{as_int}D"}}}
        return {"expr": {"Literal": {"Value": f"{value}D"}}}
    escaped = str(value).replace("'", "''")
    return {"expr": {"Literal": {"Value": f"'{escaped}'"}}}


def literal_value(node: Any) -> Any | None:
    """Decode a PBIR literal expression, or None if the node is not a literal."""
    if not isinstance(node, dict):
        return None
    expr = node.get("expr") or node
    if not isinstance(expr, dict):
        return None
    literal = expr.get("Literal")
    if not isinstance(literal, dict):
        return None
    raw = literal.get("Value")
    if not isinstance(raw, str):
        return None
    if raw in {"true", "false"}:
        return raw == "true"
    if len(raw) >= 2 and raw[-1] in {"D", "L"} and _is_number(raw[:-1]):
        number = raw[:-1]
        return float(number) if raw.endswith("D") else int(number)
    if len(raw) >= 2 and raw[0] == "'" and raw[-1] == "'":
        return raw[1:-1].replace("''", "'")
    return raw


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False
