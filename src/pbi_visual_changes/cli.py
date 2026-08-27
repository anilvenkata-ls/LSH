from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .apply import apply_change_spec, load_change_spec
from .inventory import inventory_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inventory or apply scoped PBIR visual enhancements."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory_parser = subparsers.add_parser("inventory", help="List pages and visuals")
    inventory_parser.add_argument("report", type=Path)

    apply_parser = subparsers.add_parser("apply", help="Apply a visual change spec")
    apply_parser.add_argument("spec", type=Path)
    apply_parser.add_argument("--dry-run", action="store_true")
    apply_parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Resolve relative report paths from this directory (defaults to the spec folder)",
    )

    args = parser.parse_args(argv)
    if args.command == "inventory":
        rows = inventory_report(args.report)
        json.dump(rows, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    spec = load_change_spec(args.spec, repo_root=args.repo_root)
    result = apply_change_spec(spec, dry_run=args.dry_run)
    payload = {
        "ticket": spec.ticket,
        "dryRun": result.dry_run,
        "applied": [
            {
                "id": item.change_id,
                "pageName": item.page_name,
                "visualName": item.visual_name,
                "path": str(item.visual_path),
            }
            for item in result.applied
        ],
        "filesChanged": [str(item.path) for item in result.files],
    }
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
