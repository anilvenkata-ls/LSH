from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SortChange:
    query_ref: str
    direction: str = "Descending"

    def __post_init__(self) -> None:
        if self.direction not in {"Ascending", "Descending"}:
            raise ValueError(f"Unsupported sort direction: {self.direction}")
        if "." not in self.query_ref:
            raise ValueError(
                "sort.queryRef must be '<Table>.<Field>', for example "
                "'Collections.CollectedAmount'"
            )


@dataclass(frozen=True)
class VisualMatch:
    page_name: str | None = None
    page_display_name: str | None = None
    visual_name: str | None = None
    visual_type: str | None = None
    title: str | None = None
    category_label: str | None = None

    def is_empty(self) -> bool:
        return not any(
            [
                self.page_name,
                self.page_display_name,
                self.visual_name,
                self.visual_type,
                self.title,
                self.category_label,
            ]
        )


@dataclass(frozen=True)
class VisualSet:
    title: str | None = None
    title_show: bool | None = None
    title_font_size: float | None = None
    category_label: str | None = None
    hidden: bool | None = None
    tab_order: int | None = None
    sort: SortChange | None = None

    def is_empty(self) -> bool:
        return all(
            value is None
            for value in (
                self.title,
                self.title_show,
                self.title_font_size,
                self.category_label,
                self.hidden,
                self.tab_order,
                self.sort,
            )
        )


@dataclass(frozen=True)
class VisualChange:
    id: str
    description: str
    match: VisualMatch
    set: VisualSet


@dataclass(frozen=True)
class ChangeSpec:
    report: Path
    ticket: str
    changes: tuple[VisualChange, ...]


@dataclass
class FileChange:
    path: Path
    before: dict[str, Any]
    after: dict[str, Any]


@dataclass
class AppliedChange:
    change_id: str
    visual_path: Path
    page_name: str
    visual_name: str


@dataclass
class ApplyResult:
    applied: list[AppliedChange] = field(default_factory=list)
    files: list[FileChange] = field(default_factory=list)
    dry_run: bool = False
