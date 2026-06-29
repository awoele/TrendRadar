import csv
import unittest
from pathlib import Path


class RedfoxImportDataTests(unittest.TestCase):
    def test_redfox_xhs_import_has_topic_filter_labels(self):
        path = Path("data/imports/redfox_xhs_vibecoding_2026-06-29.csv")
        self.assertTrue(path.exists(), "RedFox 小红书导入文件不存在")

        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertGreater(len(rows), 0)
        required_fields = {
            "case_type",
            "built_thing",
            "tool_stack",
            "target_audience",
            "hook",
            "content_value",
            "risk_flag",
            "hot_score",
            "recent_hot_score",
        }
        self.assertTrue(required_fields.issubset(rows[0].keys()))

        tagged_rows = [
            row
            for row in rows
            if row.get("case_type") and (row.get("built_thing") or row.get("tool_stack") or row.get("hook"))
        ]
        self.assertEqual(len(tagged_rows), len(rows))


if __name__ == "__main__":
    unittest.main()
