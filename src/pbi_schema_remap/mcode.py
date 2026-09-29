"""Rewrite schema references inside Power Query (M) expressions and SQL text."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

DEFAULT_TARGET_SCHEMA = "athena_integration"

_M_WS_ESCAPE = r"#\((?:cr,lf|lf|cr|tab)\)"
_WS = rf"(?:\s|{_M_WS_ESCAPE})+"
_SQL_IDENT = r'(?:\[[^\]]+\]|"[^"]+"|`[^`]+`|[A-Za-z_][\w$]*)'
_SQL_TABLE_REF = re.compile(
    rf"\b(FROM|JOIN|INTO|UPDATE)({_WS})({_SQL_IDENT})\.({_SQL_IDENT})(?:\.({_SQL_IDENT}))?",
    re.IGNORECASE,
)
# `FROM` inside these calls is not a table reference, e.g. EXTRACT(YEAR FROM o.order_date).
_FROM_FUNCTION_CONTEXT = re.compile(
    r"\b(?:EXTRACT|SUBSTRING|TRIM|POSITION|OVERLAY)\s*\([^()]*$", re.IGNORECASE
)
_LOOKS_LIKE_SQL = re.compile(r"\b(?:SELECT|WITH)\b", re.IGNORECASE)
_SIMPLE_IDENT = re.compile(r"^[A-Za-z_][\w$]*$")

_M_STRING = re.compile(r'"(?:[^"]|"")*"')
_M_VAR = r'(?:#"(?:[^"]|"")*"|[A-Za-z_][\w.]*)'
_SCHEMA_ITEM_NAV = re.compile(r'\{\s*\[([^\]]*?\bSchema\s*=\s*"(?:[^"]|"")*"[^\]]*)\]\s*\}')
_SCHEMA_FIELD = re.compile(r'(\bSchema\s*=\s*")((?:[^"]|"")*)(")')
_ITEM_FIELD = re.compile(r'\bItem\s*=\s*"((?:[^"]|"")*)"')
_NAME_NAV = re.compile(r'(\{\s*\[\s*Name\s*=\s*")((?:[^"]|"")*)(")')
_DB_SOURCE_ASSIGN = re.compile(
    rf"({_M_VAR})\s*=\s*(?:AmazonRedshift|PostgreSQL)\.Database\s*\("
)
_SQL_DATABASE_CALL = re.compile(r"\bSql\.Database\s*\(")
_QUERY_OPTION = re.compile(r'\bQuery\s*=\s*("(?:[^"]|"")*")')


@dataclass
class Change:
    location: str
    kind: str
    old: str
    new: str

    def __str__(self) -> str:
        return f"{self.location}: [{self.kind}] {self.old} -> {self.new}"


@dataclass
class Remapper:
    """Points every source table reference at ``target_schema``, keeping the table name.

    When ``redshift_server`` and ``redshift_database`` are set, SQL Server sources
    (``Sql.Database``) are also switched to ``AmazonRedshift.Database``.
    """

    target_schema: str = DEFAULT_TARGET_SCHEMA
    only_schemas: set[str] | None = None
    redshift_server: str | None = None
    redshift_database: str | None = None
    lowercase_tables: bool = False
    changes: list[Change] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if bool(self.redshift_server) != bool(self.redshift_database):
            raise ValueError("redshift_server and redshift_database must be given together")
        if self.only_schemas is not None:
            self.only_schemas = {s.lower() for s in self.only_schemas}

    @property
    def switch_connector(self) -> bool:
        return bool(self.redshift_server)

    def _selected(self, schema: str) -> bool:
        if schema == self.target_schema:
            return False
        return self.only_schemas is None or schema.lower() in self.only_schemas

    def _record(self, location: str, kind: str, old: str, new: str) -> None:
        self.changes.append(Change(location, kind, old, new))

    def rewrite_m(self, m: str, location: str) -> str:
        if self.switch_connector:
            m = self._switch_sql_database(m, location)
        else:
            m = self._rewrite_schema_item_nav(m, location)
        m = self._rewrite_name_nav(m, location)
        return self._rewrite_sql_literals(m, location)

    def _rewrite_schema_item_nav(self, m: str, location: str) -> str:
        """SQL Server style navigation: ``Source{[Schema="dbo",Item="Claims"]}[Data]``."""

        def field_repl(match: re.Match[str]) -> str:
            schema = _m_unescape(match.group(2))
            if not self._selected(schema):
                return match.group(0)
            self._record(location, "navigation", schema, self.target_schema)
            return match.group(1) + _m_escape(self.target_schema) + match.group(3)

        return _SCHEMA_ITEM_NAV.sub(lambda nav: _SCHEMA_FIELD.sub(field_repl, nav.group(0)), m)

    def _rewrite_name_nav(self, m: str, location: str) -> str:
        """Schema step of a Redshift/PostgreSQL navigation: ``Source{[Name="public"]}[Data]``."""
        spans = []
        for match in _DB_SOURCE_ASSIGN.finditer(m):
            var = re.escape(match.group(1))
            spans += [
                (nav.start(1), nav.end(1))
                for nav in re.finditer(rf'(?<![\w."]){var}\s*(\{{\s*\[\s*Name\s*=\s*")', m)
            ]
        for match in re.finditer(r"\b(?:AmazonRedshift|PostgreSQL)\.Database\s*\(", m):
            close = _find_close(m, match.end() - 1)
            nav = _NAME_NAV.match(m, close + 1) if close is not None else None
            if nav:
                spans.append((nav.start(1), nav.end(1)))

        for start, end in sorted(set(spans), reverse=True):
            nav = _NAME_NAV.match(m, start)
            if nav is None or nav.end(1) != end:
                continue
            schema = _m_unescape(nav.group(2))
            if not self._selected(schema):
                continue
            self._record(location, "navigation", schema, self.target_schema)
            m = m[: nav.start(2)] + _m_escape(self.target_schema) + m[nav.end(2) :]
        return m

    def _switch_sql_database(self, m: str, location: str) -> str:
        redshift = (
            f"AmazonRedshift.Database({_m_literal(self.redshift_server)}, "
            f"{_m_literal(self.redshift_database)})"
        )
        pos = 0
        while match := _SQL_DATABASE_CALL.search(m, pos):
            close = _find_close(m, match.end() - 1)
            if close is None:
                break
            args = m[match.end() : close]
            query = _QUERY_OPTION.search(args)
            if query:
                new_call = f"Value.NativeQuery({redshift}, {query.group(1)}, null, [EnableFolding=true])"
            else:
                new_call = redshift
            options = set(re.findall(r"[\[,]\s*(\w+)\s*=", _M_STRING.sub('""', args)))
            if options - {"Query"}:
                self.warnings.append(
                    f"{location}: Sql.Database options dropped: {', '.join(sorted(options - {'Query'}))}"
                )
            self._record(location, "connector", f"Sql.Database({args.strip()[:80]})", redshift)
            m = m[: match.start()] + new_call + m[close + 1 :]
            pos = match.start() + len(new_call)

        def nav_repl(nav: re.Match[str]) -> str:
            body = nav.group(1)
            schema = _m_unescape(_SCHEMA_FIELD.search(body).group(2))
            item = _ITEM_FIELD.search(body)
            if item is None or not self._selected(schema):
                return nav.group(0)
            table = _m_unescape(item.group(1))
            if self.lowercase_tables:
                table = table.lower()
            self._record(location, "navigation", f"{schema}.{item.group(1)}", f"{self.target_schema}.{table}")
            return (
                f"{{[Name={_m_literal(self.target_schema)}]}}[Data]"
                f"{{[Name={_m_literal(table)}]}}"
            )

        return _SCHEMA_ITEM_NAV.sub(nav_repl, m)

    def _rewrite_sql_literals(self, m: str, location: str) -> str:
        def repl(literal: re.Match[str]) -> str:
            raw = literal.group(0)[1:-1]
            if not _LOOKS_LIKE_SQL.search(raw):
                return literal.group(0)
            new = _m_escape(self.rewrite_sql(_m_unescape(raw), location))
            return f'"{new}"'

        return _M_STRING.sub(repl, m)

    def rewrite_sql(self, sql: str, location: str) -> str:
        def repl(match: re.Match[str]) -> str:
            if match.group(1).upper() == "FROM" and _FROM_FUNCTION_CONTEXT.search(
                sql[: match.start()]
            ):
                return match.group(0)
            *qualifiers, table = [p for p in match.group(3, 4, 5) if p]
            schema = _strip_sql_quotes(qualifiers[-1])
            if not self._selected(schema):
                return match.group(0)
            new_ref = f"{self.target_schema}.{_redshift_ident(table)}"
            old_ref = ".".join(p for p in match.group(3, 4, 5) if p)
            self._record(location, "sql", old_ref, new_ref)
            return f"{match.group(1)}{match.group(2)}{new_ref}"

        return _SQL_TABLE_REF.sub(repl, sql)


def _find_close(text: str, open_idx: int) -> int | None:
    """Index of the bracket closing ``text[open_idx]``, skipping M strings and comments."""
    pairs = {"(": ")", "[": "]", "{": "}"}
    stack = [pairs[text[open_idx]]]
    i = open_idx + 1
    while i < len(text):
        c = text[i]
        if c == '"':
            end = _M_STRING.match(text, i)
            i = end.end() if end else len(text)
            continue
        if text.startswith("//", i):
            nl = text.find("\n", i)
            i = len(text) if nl < 0 else nl
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = len(text) if end < 0 else end + 2
            continue
        if c in pairs:
            stack.append(pairs[c])
        elif c in ")]}":
            if c != stack.pop():
                return None
            if not stack:
                return i
        i += 1
    return None


def _m_unescape(raw: str) -> str:
    return raw.replace('""', '"')


def _m_escape(text: str) -> str:
    return text.replace('"', '""')


def _m_literal(text: str) -> str:
    return f'"{_m_escape(text)}"'


def _strip_sql_quotes(ident: str) -> str:
    if ident[:1] in '["`' and len(ident) >= 2:
        return ident[1:-1]
    return ident


def _redshift_ident(ident: str) -> str:
    """Redshift has no ``[bracket]`` or backtick quoting; fall back to ANSI double quotes."""
    if ident.startswith('"'):
        return ident
    name = _strip_sql_quotes(ident)
    return name if _SIMPLE_IDENT.match(name) else f'"{name}"'
