from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pbi_visual_changes.apply import (
    ChangeApplyError,
    apply_change_spec,
    load_change_spec,
    snapshot_report_files,
)
from pbi_visual_changes.cli import main
from pbi_visual_changes.inventory import inventory_report, load_json
from pbi_visual_changes.literals import literal_value


FIXTURE_REPORT = ROOT / "reports" / "fixtures" / "sample-collections.Report"
FIXTURE_SPEC = ROOT / "reports" / "fixtures" / "sample-collections.visual-changes.json"


class InventoryTests(unittest.TestCase):
    def test_lists_sample_visuals(self) -> None:
        rows = inventory_report(FIXTURE_REPORT)
        names = {row["visualName"] for row in rows}
        self.assertEqual(names, {"collectionsKpi", "agingTable", "regionSlicer"})
        kpi = next(row for row in rows if row["visualName"] == "collectionsKpi")
        self.assertEqual(kpi["title"], "Collections")
        self.assertEqual(kpi["categoryLabel"], "Collected $")
        self.assertEqual(kpi["visualType"], "cardVisual")


class ApplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = Path(tempfile.mkdtemp())
        self.report = self.temp / "sample-collections.Report"
        shutil.copytree(FIXTURE_REPORT, self.report)
        spec_payload = json.loads(FIXTURE_SPEC.read_text(encoding="utf-8"))
        spec_payload["report"] = str(self.report)
        self.spec_path = self.temp / "changes.json"
        self.spec_path.write_text(json.dumps(spec_payload), encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp)

    def test_dry_run_does_not_write(self) -> None:
        spec = load_change_spec(self.spec_path)
        before = (self.report / "definition/pages/overview/visuals/collectionsKpi/visual.json").read_text(
            encoding="utf-8"
        )
        result = apply_change_spec(spec, dry_run=True)
        after = (self.report / "definition/pages/overview/visuals/collectionsKpi/visual.json").read_text(
            encoding="utf-8"
        )
        self.assertTrue(result.dry_run)
        self.assertEqual(len(result.applied), 3)
        self.assertEqual(before, after)

    def test_applies_titles_labels_sort_and_tab_order(self) -> None:
        spec = load_change_spec(self.spec_path)
        before = snapshot_report_files(self.report)
        slicer_before = json.loads(
            before[self.report / "definition/pages/overview/visuals/regionSlicer/visual.json"]
        )
        result = apply_change_spec(spec)
        after = snapshot_report_files(self.report)
        changed = [path for path, text in after.items() if before[path] != text]
        self.assertEqual({path.parent.name for path in changed}, {
            "collectionsKpi",
            "agingTable",
            "regionSlicer",
        })
        self.assertTrue(all(path.name == "visual.json" for path in changed))
        self.assertEqual([item.change_id for item in result.applied], [
            "kpi-title",
            "aging-sort",
            "region-slicer-tab",
        ])
        self.assertEqual(len(result.files), 3)

        kpi = load_json(self.report / "definition/pages/overview/visuals/collectionsKpi/visual.json")
        title = kpi["visual"]["visualContainerObjects"]["title"][0]["properties"]
        self.assertEqual(literal_value(title["text"]), "Patient Collections")
        self.assertEqual(literal_value(title["fontSize"]), 14.0)
        self.assertEqual(
            literal_value(kpi["visual"]["objects"]["label"][0]["properties"]["text"]),
            "Collected Amount",
        )
        self.assertEqual(
            kpi["visual"]["query"]["queryState"]["Data"]["projections"][0]["queryRef"],
            "Collections.CollectedAmount",
        )

        aging = load_json(self.report / "definition/pages/overview/visuals/agingTable/visual.json")
        sort = aging["visual"]["query"]["sortDefinition"][0]
        self.assertEqual(sort["direction"], "Descending")
        self.assertEqual(sort["field"]["Measure"]["Property"], "Balance")

        slicer = load_json(self.report / "definition/pages/overview/visuals/regionSlicer/visual.json")
        self.assertEqual(slicer["position"]["tabOrder"], 100)
        self.assertEqual(slicer["visual"]["query"], slicer_before["visual"]["query"])

    def test_rejects_ambiguous_match(self) -> None:
        payload = json.loads(self.spec_path.read_text(encoding="utf-8"))
        payload["changes"] = [
            {
                "id": "too-broad",
                "match": {"pageDisplayName": "Overview"},
                "set": {"title": "Nope"},
            }
        ]
        self.spec_path.write_text(json.dumps(payload), encoding="utf-8")
        spec = load_change_spec(self.spec_path)
        with self.assertRaises(ChangeApplyError) as ctx:
            apply_change_spec(spec)
        self.assertIn("matched 3 visual(s)", str(ctx.exception))

    def test_empty_patient_collections_spec_is_rejected(self) -> None:
        path = ROOT / "reports" / "patient-collections" / "visual-changes.json"
        with self.assertRaises(ChangeApplyError):
            load_change_spec(path, repo_root=ROOT)

    def test_cli_inventory_and_dry_run(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout

        with redirect_stdout(StringIO()) as stdout:
            code = main(["inventory", str(self.report)])
        self.assertEqual(code, 0)
        rows = json.loads(stdout.getvalue())
        self.assertEqual(len(rows), 3)

        with redirect_stdout(StringIO()) as stdout:
            code = main(["apply", str(self.spec_path), "--dry-run"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["dryRun"])
        self.assertEqual(len(payload["applied"]), 3)


class LiteralTests(unittest.TestCase):
    def test_round_trip_strings_and_numbers(self) -> None:
        from pbi_visual_changes.literals import pbi_literal

        self.assertEqual(literal_value(pbi_literal("AR Aging")), "AR Aging")
        self.assertEqual(literal_value(pbi_literal(14.0)), 14.0)
        self.assertEqual(literal_value(pbi_literal(True)), True)


if __name__ == "__main__":
    unittest.main()
