import csv
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_pages_artifact import _imported_search_content
from scripts.fetch_tikhub_douyin_search import (
    API_URL,
    SOURCE_NAME,
    build_request_body,
    load_keyword_rules,
    parse_search_items,
    write_rows_csv,
)


class TikHubDouyinSearchTests(unittest.TestCase):
    def test_parse_video_search_items_maps_aweme_info_to_standard_import_row(self):
        payload = {
            "data": {
                "data": [
                    {
                        "type": 1,
                        "aweme_info": {
                            "aweme_id": "733123456789",
                            "desc": "用 Cursor 做 vibe coding 选题库",
                            "create_time": 1710000000,
                            "author": {"nickname": "Vibe Creator"},
                            "video": {
                                "cover": {
                                    "url_list": ["https://img.example.com/cover.jpg"]
                                }
                            },
                            "statistics": {
                                "digg_count": 123,
                                "comment_count": 4,
                                "collect_count": 5,
                                "share_count": 6,
                            },
                        },
                    }
                ]
            }
        }

        rows = parse_search_items(payload, keyword="vibe coding", today="2026-06-30")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["platform"], "douyin")
        self.assertEqual(rows[0]["title"], "用 Cursor 做 vibe coding 选题库")
        self.assertEqual(rows[0]["url"], "https://www.douyin.com/video/733123456789")
        self.assertEqual(rows[0]["cover_url"], "https://img.example.com/cover.jpg")
        self.assertEqual(rows[0]["author"], "Vibe Creator")
        self.assertEqual(rows[0]["published_at"], "2024-03-10")
        self.assertEqual(rows[0]["like_count"], "123")
        self.assertEqual(rows[0]["comment_count"], "4")
        self.assertEqual(rows[0]["collect_count"], "5")
        self.assertEqual(rows[0]["share_count"], "6")
        self.assertEqual(rows[0]["source"], SOURCE_NAME)
        self.assertEqual(rows[0]["keyword"], "vibe coding")

    def test_keyword_search_rows_enter_content_pool_but_hot_rows_do_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            import_dir = Path(tmp)
            fields = [
                "platform",
                "title",
                "url",
                "cover_url",
                "author",
                "published_at",
                "like_count",
                "comment_count",
                "collect_count",
                "share_count",
                "description",
                "source",
                "keyword",
            ]
            with (import_dir / "douyin.csv").open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerow(
                    {
                        "platform": "douyin",
                        "title": "vibe coding 抖音关键词结果",
                        "url": "https://www.douyin.com/video/1",
                        "cover_url": "https://img.example.com/1.jpg",
                        "source": SOURCE_NAME,
                        "keyword": "vibe coding",
                    }
                )
                writer.writerow(
                    {
                        "platform": "douyin",
                        "title": "不应进入内容池的热榜",
                        "url": "https://www.douyin.com/hot/1",
                        "source": "tikhub:douyin_hot_search",
                    }
                )

            content = _imported_search_content(import_dir)

        self.assertEqual([item["title"] for item in content["items"]], ["vibe coding 抖音关键词结果"])
        self.assertEqual(content["items"][0]["platform_id"], "douyin-search")
        self.assertEqual(content["items"][0]["source"], SOURCE_NAME)

    def test_request_body_uses_keyword_search_defaults_not_hot_search(self):
        body = build_request_body(keyword="vibe coding", publish_time="7")

        self.assertEqual(API_URL, "https://api.tikhub.io/api/v1/douyin/search/fetch_video_search_v2")
        self.assertEqual(body["keyword"], "vibe coding")
        self.assertEqual(body["publish_time"], "7")
        self.assertEqual(body["content_type"], "0")

    def test_load_keyword_rules_reads_frequency_words_and_global_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            keyword_file = Path(tmp) / "frequency_words.txt"
            keyword_file.write_text(
                "\n".join(
                    [
                        "Codex",
                        "+AI",
                        "!ignore-before-global",
                        "@10",
                        "[GLOBAL_FILTER]",
                        "土区续费",
                    ]
                ),
                encoding="utf-8",
            )

            keywords, excludes = load_keyword_rules(keyword_file)

            self.assertEqual(keywords, ["Codex", "AI"])
            self.assertEqual(excludes, ["土区续费"])

    def test_writes_standard_csv_for_downstream_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "douyin.csv"
            write_rows_csv(
                out,
                [
                    {
                        "platform": "douyin",
                        "title": "vibe coding",
                        "url": "https://www.douyin.com/video/1",
                        "source": SOURCE_NAME,
                    }
                ],
            )

            with out.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(rows[0]["platform"], "douyin")
        self.assertEqual(rows[0]["title"], "vibe coding")
        self.assertIn("cover_url", rows[0])
        self.assertIn("description", rows[0])

    def test_env_local_is_ignored_by_git(self):
        gitignore = Path(".gitignore").read_text(encoding="utf-8")

        self.assertIn(".env.local", gitignore.splitlines())


if __name__ == "__main__":
    unittest.main()
