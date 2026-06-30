import csv
import unittest
from pathlib import Path

from scripts.prepare_pages_artifact import _imported_search_content


class DouyinImportDataTests(unittest.TestCase):
    def test_douyin_search_import_is_tagged_topic_data(self):
        path = Path("data/imports/douyin_vibecoding_tagged_2026-05-16_2026-06-15.csv")
        self.assertTrue(path.exists(), "抖音搜索导入应先打标后再进入内容面板")

        legacy_raw_files = sorted(Path("data/imports").glob("douyin_vibecoding_2026-*.csv"))
        self.assertEqual(legacy_raw_files, [], "裸抖音搜索 CSV 不应再作为默认导入源")

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

        for row in rows:
            self.assertEqual(row.get("platform"), "douyin")
            self.assertTrue(row.get("case_type"))
            self.assertTrue(row.get("built_thing") or row.get("tool_stack") or row.get("hook"))

    def test_imported_douyin_topic_items_have_filter_tags_after_dedupe(self):
        content = _imported_search_content(Path("data/imports"))
        douyin_search_items = [
            item
            for item in content["items"]
            if item.get("platform_id") == "douyin-search"
            and item.get("source") != "tikhub:douyin_keyword_search"
        ]
        missing_tags = [
            item
            for item in content["items"]
            if item.get("platform_id") == "douyin-topic"
            and not (
                item.get("case_type")
                and (item.get("built_thing") or item.get("tool_stack") or item.get("hook"))
            )
        ]

        self.assertEqual(douyin_search_items, [])
        self.assertEqual(
            [(item.get("title"), item.get("url")) for item in missing_tags],
            [],
        )


if __name__ == "__main__":
    unittest.main()
