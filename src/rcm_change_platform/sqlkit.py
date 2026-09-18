"""Structure aware SQL editing helpers.

The change generation agent must add a column to an existing projection, to an
INSERT column list and occasionally add a join, without disturbing the rest of a
hand written stored procedure. These helpers work on spans discovered by a small
scanner that understands string literals, comments, parentheses and CASE blocks,
which is enough for the warehouse SQL this platform edits and far more reliable
than line based regular expressions.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass


class SqlEditError(RuntimeError):
    """Raised when the requested edit cannot be applied safely."""


_WORD = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")


@dataclass(frozen=True)
class Token:
    start: int
    end: int
    word: str
    depth: int


def scan(sql: str) -> list[Token]:
    """Tokenise identifiers/keywords with their nesting depth.

    Depth counts parentheses plus open ``CASE`` blocks so that a ``CASE`` used in
    a projection never hides the ``FROM`` keyword that terminates it.
    """

    tokens: list[Token] = []
    depth = 0
    index = 0
    length = len(sql)
    while index < length:
        char = sql[index]
        if char in "'\"":
            quote = char
            index += 1
            while index < length:
                if sql[index] == quote:
                    if quote == "'" and index + 1 < length and sql[index + 1] == "'":
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            continue
        if sql.startswith("--", index):
            newline = sql.find("\n", index)
            index = length if newline == -1 else newline
            continue
        if sql.startswith("/*", index):
            close = sql.find("*/", index)
            index = length if close == -1 else close + 2
            continue
        if char == "(":
            depth += 1
            index += 1
            continue
        if char == ")":
            depth = max(0, depth - 1)
            index += 1
            continue
        match = _WORD.match(sql, index)
        if match:
            word = match.group(0)
            upper = word.upper()
            if upper == "CASE":
                tokens.append(Token(match.start(), match.end(), upper, depth))
                depth += 1
            elif upper == "END":
                depth = max(0, depth - 1)
                tokens.append(Token(match.start(), match.end(), upper, depth))
            else:
                tokens.append(Token(match.start(), match.end(), upper, depth))
            index = match.end()
            continue
        index += 1
    return tokens


def projection_span(sql: str, occurrence: int = 0) -> tuple[int, int]:
    """Return the character span of the projection list of a ``SELECT``."""

    tokens = scan(sql)
    selects = [t for t in tokens if t.word == "SELECT"]
    if occurrence >= len(selects):
        raise SqlEditError(f"SQL has no SELECT at index {occurrence}")
    select = selects[occurrence]
    for token in tokens:
        if token.start > select.end and token.word == "FROM" and token.depth == select.depth:
            return select.end, token.start
    raise SqlEditError("SELECT is not terminated by a FROM at the same nesting depth")


def split_projection(projection: str) -> list[str]:
    """Split a projection list on top level commas."""

    items: list[str] = []
    depth = 0
    current = []
    index = 0
    length = len(projection)
    while index < length:
        char = projection[index]
        if char in "'\"":
            quote = char
            current.append(char)
            index += 1
            while index < length:
                current.append(projection[index])
                if projection[index] == quote:
                    index += 1
                    break
                index += 1
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            items.append("".join(current))
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    items.append("".join(current))
    return items


def _indent_of(fragment: str) -> str:
    lines = [line for line in fragment.splitlines() if line.strip()]
    if not lines:
        return "    "
    last = lines[-1]
    return last[: len(last) - len(last.lstrip())] or "    "


def add_projection_column(sql: str, expression: str, occurrence: int = 0) -> str:
    """Append ``expression`` as the last item of a SELECT projection."""

    start, end = projection_span(sql, occurrence)
    projection = sql[start:end]
    items = split_projection(projection)
    last = items[-1]
    trailing_ws = last[len(last.rstrip()) :]
    indent = _indent_of(projection)
    if "\n" in projection:
        addition = f",\n{indent}{expression}"
    else:
        addition = f", {expression}"
    rebuilt = projection[: len(projection) - len(trailing_ws)] + addition + trailing_ws
    return sql[:start] + rebuilt + sql[end:]


def insert_column_list_span(sql: str) -> tuple[int, int]:
    """Return the span inside the parentheses of an ``INSERT INTO t (...)``."""

    match = re.search(r"INSERT\s+INTO\s+[A-Za-z_][\w.\"]*\s*\(", sql, re.IGNORECASE)
    if not match:
        raise SqlEditError("No INSERT INTO column list found")
    open_paren = match.end() - 1
    depth = 0
    for index in range(open_paren, len(sql)):
        if sql[index] == "(":
            depth += 1
        elif sql[index] == ")":
            depth -= 1
            if depth == 0:
                return open_paren + 1, index
    raise SqlEditError("Unbalanced parentheses in INSERT column list")


def add_insert_column(sql: str, column: str) -> str:
    start, end = insert_column_list_span(sql)
    body = sql[start:end]
    trailing_ws = body[len(body.rstrip()) :]
    indent = _indent_of(body)
    if "\n" in body:
        addition = f",\n{indent}{column}"
    else:
        addition = f", {column}"
    rebuilt = body[: len(body) - len(trailing_ws)] + addition + trailing_ws
    return sql[:start] + rebuilt + sql[end:]


_FROM_TERMINATORS = {"WHERE", "GROUP", "HAVING", "ORDER", "LIMIT", "UNION", "END"}


def from_clause_span(sql: str, occurrence: int = 0) -> tuple[int, int]:
    """Span of the FROM clause belonging to the ``occurrence``-th SELECT.

    Anchoring on the SELECT matters: a stored procedure that starts with
    ``DELETE FROM target`` has a FROM that belongs to no projection at all.
    """

    _, from_start = projection_span(sql, occurrence)
    tokens = scan(sql)
    start_token = next((t for t in tokens if t.start == from_start and t.word == "FROM"), None)
    if start_token is None:
        raise SqlEditError("Could not locate the FROM clause for the requested SELECT")
    end = len(sql)
    for token in tokens:
        if token.start > start_token.end and token.depth == start_token.depth and token.word in _FROM_TERMINATORS:
            end = token.start
            break
    semicolon = sql.find(";", start_token.end)
    if semicolon != -1:
        end = min(end, semicolon)
    return start_token.start, end


def add_join(sql: str, join_clause: str, occurrence: int = 0) -> str:
    """Append a join to the FROM clause of a SELECT, preserving indentation."""

    start, end = from_clause_span(sql, occurrence)
    clause = sql[start:end]
    trailing_ws = clause[len(clause.rstrip()) :]
    lines = [line for line in clause.splitlines() if line.strip()]
    indent = ""
    if len(lines) > 1:
        last = lines[-1]
        indent = last[: len(last) - len(last.lstrip())]
    separator = f"\n{indent}" if "\n" in clause else " "
    rebuilt = clause[: len(clause) - len(trailing_ws)] + separator + join_clause + trailing_ws
    return sql[:start] + rebuilt + sql[end:]


def alias_for_table(sql: str, table: str) -> str | None:
    """Find the alias assigned to ``table`` in a FROM/JOIN clause."""

    pattern = re.compile(
        rf"(?:FROM|JOIN)\s+{re.escape(table)}\s+(?:AS\s+)?([A-Za-z_][A-Za-z_0-9]*)",
        re.IGNORECASE,
    )
    match = pattern.search(sql)
    if not match:
        return None
    candidate = match.group(1)
    if candidate.upper() in {"ON", "JOIN", "INNER", "LEFT", "RIGHT", "WHERE", "GROUP", "ORDER"}:
        return None
    return candidate


def used_aliases(sql: str) -> set[str]:
    pattern = re.compile(
        r"(?:FROM|JOIN)\s+[A-Za-z_][\w.\"]*\s+(?:AS\s+)?([A-Za-z_][A-Za-z_0-9]*)",
        re.IGNORECASE,
    )
    found = set()
    for match in pattern.finditer(sql):
        candidate = match.group(1)
        if candidate.upper() not in {"ON", "JOIN", "INNER", "LEFT", "RIGHT", "WHERE", "GROUP", "ORDER"}:
            found.add(candidate.lower())
    return found


def suggest_alias(sql: str, table: str) -> str:
    base = table.split(".")[-1]
    base = re.sub(r"^(dim|fact|stg)_", "", base)
    seed = "".join(part[0] for part in base.split("_") if part) or "t"
    taken = used_aliases(sql)
    if seed not in taken:
        return seed
    for suffix in range(2, 50):
        candidate = f"{seed}{suffix}"
        if candidate not in taken:
            return candidate
    raise SqlEditError("Unable to allocate a unique table alias")


def statements(sql: str) -> list[str]:
    """Split a script into statements on top level semicolons."""

    parts: list[str] = []
    current: list[str] = []
    depth = 0
    index = 0
    length = len(sql)
    while index < length:
        char = sql[index]
        if char in "'\"":
            quote = char
            current.append(char)
            index += 1
            while index < length:
                current.append(sql[index])
                if sql[index] == quote:
                    index += 1
                    break
                index += 1
            continue
        if sql.startswith("--", index):
            newline = sql.find("\n", index)
            stop = length if newline == -1 else newline
            current.append(sql[index:stop])
            index = stop
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == ";" and depth == 0:
            parts.append("".join(current).strip())
            current = []
            index += 1
            continue
        current.append(char)
        index += 1
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return [part for part in parts if part]


def strip_comments(sql: str) -> str:
    """Remove line comments, leaving the executable text."""

    lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    return "\n".join(lines).strip()


def is_executable(statement: str) -> bool:
    return bool(strip_comments(statement))


_PROC_HEADER = re.compile(
    r"^\s*CREATE\s+(?:OR\s+REPLACE\s+)?PROCEDURE.*?\$\$\s*(?:BEGIN)?",
    re.IGNORECASE | re.DOTALL,
)
_PROC_FOOTER = re.compile(r"END;?\s*\$\$\s*LANGUAGE\s+\w+\s*;?\s*$", re.IGNORECASE)


def procedure_body(sql: str) -> str:
    """Strip the ``CREATE PROCEDURE`` wrapper, returning the executable body."""

    inner = _PROC_HEADER.sub("", sql, count=1)
    inner = _PROC_FOOTER.sub("", inner)
    return inner.strip()


def unified_diff(before: str, after: str, name: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{name}",
            tofile=f"b/{name}",
        )
    )
