"""Small text utilities used for matching business language to physical metadata."""

from __future__ import annotations

import difflib
import re
from typing import Iterable, Sequence

_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "by",
        "for",
        "from",
        "in",
        "of",
        "on",
        "please",
        "the",
        "to",
        "with",
        "report",
        "column",
        "field",
        "add",
        "new",
    }
)


def normalize(value: str) -> str:
    return " ".join(_TOKEN_SPLIT.split(value.lower())).strip()


def tokens(value: str, drop_stopwords: bool = False) -> list[str]:
    parts = [p for p in _TOKEN_SPLIT.split(value.lower()) if p]
    if drop_stopwords:
        parts = [p for p in parts if p not in _STOPWORDS]
    return parts


def similarity(left: str, right: str) -> float:
    """Blend token overlap with sequence similarity, returning 0.0 - 1.0."""

    left_norm, right_norm = normalize(left), normalize(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0

    left_tokens = set(tokens(left_norm, drop_stopwords=True)) or set(tokens(left_norm))
    right_tokens = set(tokens(right_norm, drop_stopwords=True)) or set(tokens(right_norm))
    overlap = len(left_tokens & right_tokens)
    jaccard = overlap / len(left_tokens | right_tokens) if left_tokens | right_tokens else 0.0
    containment = overlap / min(len(left_tokens), len(right_tokens)) if left_tokens and right_tokens else 0.0
    ratio = difflib.SequenceMatcher(None, left_norm, right_norm).ratio()
    return round(max(ratio, 0.5 * jaccard + 0.5 * containment), 4)


def best_match(
    query: str,
    candidates: Iterable[tuple[str, Sequence[str]]],
    threshold: float = 0.45,
) -> tuple[str | None, float, list[tuple[str, float]]]:
    """Pick the candidate whose aliases best match ``query``.

    Returns the winning key, its score and every candidate scored in descending
    order so callers can surface near misses as clarification options.
    """

    scored: list[tuple[str, float]] = []
    for key, aliases in candidates:
        score = max((similarity(query, alias) for alias in aliases), default=0.0)
        scored.append((key, score))
    scored.sort(key=lambda item: (-item[1], item[0]))
    if scored and scored[0][1] >= threshold:
        return scored[0][0], scored[0][1], scored
    return None, (scored[0][1] if scored else 0.0), scored


def title_case(value: str) -> str:
    return " ".join(word.capitalize() for word in tokens(value))
