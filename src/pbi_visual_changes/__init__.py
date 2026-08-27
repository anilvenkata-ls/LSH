"""Apply scoped Power BI PBIR visual enhancements as code."""

from .apply import apply_change_spec, load_change_spec
from .inventory import inventory_report
from .models import ApplyResult, ChangeSpec, VisualChange

__all__ = [
    "ApplyResult",
    "ChangeSpec",
    "VisualChange",
    "apply_change_spec",
    "inventory_report",
    "load_change_spec",
]
