"""Command line entry point: ``rcm-change``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .catalog import LineageGraph, MetadataRepository
from .context import RunOptions
from .llm import default_client
from .models import ImpactAction, TestStatus
from .orchestrator import run_change_request

EXIT_OK = 0
EXIT_BLOCKED = 1
EXIT_HALTED = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rcm-change",
        description="AI-powered change automation for the RCM data platform.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run the full agent pipeline for a business request.")
    run.add_argument("request", help='Natural language request, e.g. "Add Patient Financial Class to AR Aging Report"')
    run.add_argument("--output", "-o", default="out", help="Directory that receives the Change_Request package")
    run.add_argument("--metadata-dir", help="Directory of metadata JSON files (defaults to the bundled catalog)")
    run.add_argument("--reason", default="", help="Business reason recorded on the requirement")
    run.add_argument("--requested-by", default="business_user", help="Requester recorded on the requirement")
    run.add_argument("--request-id", default="", help="Override the generated request id")
    run.add_argument("--release", default="", help="Release label used in the release notes")
    run.add_argument("--no-execute", action="store_true", help="Generate artifacts without running the sandbox tests")
    run.add_argument("--json", action="store_true", help="Print the run summary as JSON")

    catalog = subparsers.add_parser("catalog", help="Inspect the metadata catalog the agents search.")
    catalog.add_argument("section", choices=["reports", "datasets", "tables", "views", "routines", "etl", "terms"])
    catalog.add_argument("--metadata-dir")

    lineage = subparsers.add_parser("lineage", help="Show the lineage around a catalog object.")
    lineage.add_argument("object_name")
    lineage.add_argument("--metadata-dir")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo = MetadataRepository.load(args.metadata_dir) if getattr(args, "metadata_dir", None) else MetadataRepository.load()

    if args.command == "catalog":
        return _catalog(repo, args.section)
    if args.command == "lineage":
        return _lineage(repo, args.object_name)
    return _run(repo, args)


def _run(repo: MetadataRepository, args: argparse.Namespace) -> int:
    options = RunOptions(
        output_dir=Path(args.output),
        execute_tests=not args.no_execute,
        requested_by=args.requested_by,
        business_reason=args.reason,
        request_id=args.request_id,
        release=args.release,
    )
    context = run_change_request(args.request, options=options, repo=repo, llm=default_client())

    if args.json:
        print(json.dumps(context.summary(), indent=2, default=str))
    else:
        _print_report(context)

    if context.halted:
        return EXIT_HALTED
    if context.checklist and not context.checklist.ready:
        return EXIT_BLOCKED
    return EXIT_OK


def _print_report(context) -> None:
    request = context.request
    print("=" * 78)
    print("RCM CHANGE AUTOMATION PLATFORM")
    print("=" * 78)
    print(f"Request : {context.raw_request}")
    if request:
        print(f"Parsed  : column '{request.requested_column}' -> report '{request.report}' "
              f"({request.parser}, confidence {request.confidence:.2f})")
    print()

    print("Agent run")
    print("-" * 78)
    for report in context.reports:
        print(f"  {report.step:>2}. {report.agent:<24} {report.status:<10} {report.summary}")
    print()

    if context.metadata and context.metadata.column:
        column = context.metadata.column
        print("Resolved column")
        print("-" * 78)
        print(f"  {column.physical_table}.{column.physical_column} {column.data_type} "
              f"(matched on {column.matched_on}, score {column.match_score:.2f})")
        print(f"  {column.definition}")
        print()

    if context.impact:
        print("Impact matrix")
        print("-" * 78)
        width = max((len(item.object_name) for item in context.impact.items), default=10)
        for item in context.impact.items:
            print(f"  {item.object_name:<{width}}  {item.object_type:<18} {item.action.value:<10} {item.rationale}")
        modifies = [i.object_name for i in context.impact.items if i.action is ImpactAction.MODIFY]
        print(f"\n  Lineage: {' -> '.join(context.impact.propagation_path)}")
        print(f"  Code changes required for {len(modifies)} object(s)")
        print()

    for run in (context.unit_run, context.integration_run):
        if not run:
            continue
        print(f"{run.suite} ({'executed' if run.executed else 'not executed'})")
        print("-" * 78)
        for result in run.results:
            marker = {
                TestStatus.PASSED: "PASS",
                TestStatus.FAILED: "FAIL",
                TestStatus.ERROR: "ERR ",
                TestStatus.SKIPPED: "SKIP",
            }[result.status]
            detail = f" ({result.actual})" if result.actual else ""
            print(f"  [{marker}] {result.name}{detail}")
        print()

    if context.reconciliation and context.reconciliation.lines:
        print("Financial reconciliation")
        print("-" * 78)
        for line in context.reconciliation.lines:
            verdict = "PASS" if line.matched else "FAIL"
            print(f"  [{verdict}] {line.metric:<40} before={line.before:>14,.2f} after={line.after:>14,.2f}")
        print()

    if context.checklist:
        print("Deployment readiness")
        print("-" * 78)
        for item in context.checklist.items:
            print(f"  {item.marker} {item.section}: {item.item}" + (f" - {item.detail}" if item.detail else ""))
        print(f"\n  Verdict: {'READY FOR DEPLOYMENT' if context.checklist.ready else 'BLOCKED'}")
        print()

    if context.warnings:
        print("Warnings")
        print("-" * 78)
        for warning in context.warnings:
            print(f"  - {warning}")
        print()

    if context.package:
        print("Package")
        print("-" * 78)
        print(f"  {context.package.root}")
        for name in context.package.files:
            print(f"    - {name}")


def _catalog(repo: MetadataRepository, section: str) -> int:
    rows: list[tuple[str, str]]
    if section == "reports":
        rows = [(r["name"], f"dataset {r.get('dataset', '')}") for r in repo.reports]
    elif section == "datasets":
        rows = [(d["name"], f"{d.get('workspace', '')}, sources: {', '.join(d.get('sources', []))}") for d in repo.datasets]
    elif section == "tables":
        rows = [(t["name"], f"{t.get('layer', '')}, {len(t.get('columns', []))} columns") for t in repo.tables]
    elif section == "views":
        rows = [(v["name"], f"depends on {', '.join(v.get('depends_on', []))}") for v in repo.views]
    elif section == "routines":
        rows = [(r["name"], f"writes {', '.join(r.get('writes', []))}") for r in repo.routines]
    elif section == "etl":
        rows = [(c["name"], f"{c.get('object_type', '')}: {c.get('description', '')}") for c in repo.etl_components]
    else:
        rows = [
            (t["business_term"], f"{t.get('physical_table')}.{t.get('physical_column')} {t.get('data_type', '')}")
            for t in repo.terms
        ]
    width = max((len(name) for name, _ in rows), default=10)
    for name, detail in rows:
        print(f"{name:<{width}}  {detail}")
    return EXIT_OK


def _lineage(repo: MetadataRepository, object_name: str) -> int:
    graph = LineageGraph.build(repo)
    if not graph.has(object_name):
        print(f"'{object_name}' is not in the lineage graph.", file=sys.stderr)
        return EXIT_HALTED
    print(f"{object_name} ({repo.object_type(object_name)})")
    print("\nUpstream")
    for name in graph.upstream(object_name) or ["  (none)"]:
        print(f"  <- {name}")
    print("\nDownstream")
    for name in graph.downstream(object_name) or ["  (none)"]:
        print(f"  -> {name}")
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
