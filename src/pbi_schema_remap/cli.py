from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .formats import UnsupportedFileError, remap_path
from .mcode import DEFAULT_TARGET_SCHEMA, Remapper


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pbi-schema-remap",
        description=(
            "Point every source table of a Power BI semantic model at a Redshift schema "
            "(default: athena_integration), keeping the table names."
        ),
    )
    p.add_argument("input", type=Path, help=".pbip, PBIP folder, .pbit, model.bim or .tmdl file")
    p.add_argument("-o", "--output", type=Path, help="output path (default: <input>_redshift)")
    p.add_argument("--schema", default=DEFAULT_TARGET_SCHEMA, help="target Redshift schema")
    p.add_argument(
        "--only-schema",
        action="append",
        metavar="NAME",
        help="only remap this source schema (repeatable); default remaps every schema",
    )
    p.add_argument("--redshift-server", help="switch Sql.Database sources to this Redshift host")
    p.add_argument("--redshift-database", help="Redshift database used with --redshift-server")
    p.add_argument(
        "--lowercase-tables",
        action="store_true",
        help="lowercase table names when converting SQL Server navigation to Redshift",
    )
    p.add_argument("--dry-run", action="store_true", help="report changes without writing")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        remapper = Remapper(
            target_schema=args.schema,
            only_schemas=set(args.only_schema) if args.only_schema else None,
            redshift_server=args.redshift_server,
            redshift_database=args.redshift_database,
            lowercase_tables=args.lowercase_tables,
        )
        dst = remap_path(args.input, args.output, remapper, dry_run=args.dry_run)
    except (UnsupportedFileError, ValueError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for change in remapper.changes:
        print(change)
    for warning in remapper.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    verb = "would write" if args.dry_run else "wrote"
    print(f"{len(remapper.changes)} reference(s) remapped to '{args.schema}'; {verb} {dst}")
    if not remapper.changes:
        print("warning: no schema references found", file=sys.stderr)
    return 0
