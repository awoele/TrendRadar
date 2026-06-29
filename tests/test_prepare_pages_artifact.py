import json
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_pages_artifact import prepare_pages_artifact


class PreparePagesArtifactTests(unittest.TestCase):
    def test_writes_content_home_and_copies_recent_html_to_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "output"
            dest = root / "public"

            (source / "2026-06-29" / "html").mkdir(parents=True)
            (source / "2026-06-28" / "html").mkdir(parents=True)
            (source / "2026-06-20" / "html").mkdir(parents=True)
            (source / "2026-06-29" / "txt").mkdir(parents=True)

            (source / "index.html").write_text("<html>latest</html>", encoding="utf-8")
            (source / "2026-06-29" / "html" / "当日汇总.html").write_text("today", encoding="utf-8")
            (source / "2026-06-28" / "html" / "13-00.html").write_text("yesterday", encoding="utf-8")
            (source / "2026-06-20" / "html" / "old.html").write_text("old", encoding="utf-8")
            (source / "2026-06-29" / "txt" / "13-00.txt").write_text("private-ish raw text", encoding="utf-8")

            manifest = prepare_pages_artifact(source, dest, keep_days=7, import_source=root / "missing-imports")

            home_html = (dest / "index.html").read_text(encoding="utf-8")
            self.assertIn('url=content/', home_html)
            self.assertIn('window.location.replace("content/")', home_html)
            self.assertNotIn("<html>latest</html>", home_html)
            self.assertTrue((dest / "reports" / "2026-06-29" / "当日汇总.html").exists())
            self.assertTrue((dest / "reports" / "2026-06-28" / "13-00.html").exists())
            self.assertFalse((dest / "reports" / "2026-06-20" / "old.html").exists())
            self.assertFalse((dest / "2026-06-29" / "txt" / "13-00.txt").exists())

            manifest_data = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest_data["latest"], "index.html")
            self.assertEqual(len(manifest_data["reports"]), 2)
            self.assertEqual(manifest, manifest_data)

    def test_copies_config_panel_assets_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "output"
            dest = root / "public"
            panel_source = root / "web" / "config-panel"

            source.mkdir()
            panel_source.mkdir(parents=True)

            (source / "index.html").write_text("<html>latest</html>", encoding="utf-8")
            (panel_source / "index.html").write_text("<html>config</html>", encoding="utf-8")
            (panel_source / "app.js").write_text("console.log('config')", encoding="utf-8")

            manifest = prepare_pages_artifact(
                source,
                dest,
                keep_days=7,
                panel_source=panel_source,
            )

            self.assertEqual((dest / "config" / "index.html").read_text(encoding="utf-8"), "<html>config</html>")
            self.assertEqual((dest / "config" / "app.js").read_text(encoding="utf-8"), "console.log('config')")
            self.assertEqual(manifest["config_panel"], "config/index.html")

    def test_generates_public_stats_json_from_reports_and_txt_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "output"
            dest = root / "public"

            (source / "2026-06-29" / "html").mkdir(parents=True)
            (source / "2026-06-29" / "txt").mkdir(parents=True)

            latest_html = """
            <html>
              <body>
                <span class="info-label">新闻总数</span>
                <span class="info-value">5 条</span>
                <span class="info-label">热点新闻</span>
                <span class="info-value">3 条</span>
                <div class="error-section">
                  <li class="error-item">xhs</li>
                </div>
                <div class="word-group">
                  <div class="word-name">vibe coding</div>
                  <div class="word-count hot">2 条</div>
                  <span class="source-name">sspai</span>
                  <span class="source-name">juejin</span>
                </div>
                <div class="word-group">
                  <div class="word-name">Codex</div>
                  <div class="word-count">1 条</div>
                  <span class="source-name">v2ex</span>
                </div>
              </body>
            </html>
            """
            (source / "index.html").write_text(latest_html, encoding="utf-8")
            (source / "2026-06-29" / "html" / "15-43.html").write_text(latest_html, encoding="utf-8")
            (source / "2026-06-29" / "txt" / "15-43.txt").write_text(
                "\n".join(
                    [
                        "sspai | 少数派",
                        "1. First item",
                        "2. Second item",
                        "",
                        "juejin | 稀土掘金",
                        "1. Third item",
                        "",
                        "v2ex | V2EX",
                        "1. Fourth item",
                        "2. Fifth item",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = prepare_pages_artifact(source, dest, keep_days=7, import_source=root / "missing-imports")

            stats = json.loads((dest / "stats.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["stats_json"], "stats.json")
            self.assertEqual(stats["latest_report"]["path"], "index.html")
            self.assertEqual(stats["totals"]["reports"], 1)
            self.assertEqual(stats["totals"]["crawled_titles"], 5)
            self.assertEqual(stats["totals"]["matched_titles"], 3)
            self.assertEqual(stats["platforms"][0]["id"], "sspai")
            self.assertEqual(stats["platforms"][0]["crawled"], 2)
            self.assertEqual(stats["platforms"][0]["matched"], 1)
            self.assertEqual(stats["keywords"][0]["name"], "vibe coding")
            self.assertEqual(stats["keywords"][0]["matched"], 2)
            self.assertEqual(stats["failed_platforms"], ["xhs"])
            self.assertIn("generated_at", stats)

    def test_copies_stats_panel_assets_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "output"
            dest = root / "public"
            stats_panel_source = root / "web" / "stats-panel"

            source.mkdir()
            stats_panel_source.mkdir(parents=True)

            (source / "index.html").write_text("<html>latest</html>", encoding="utf-8")
            (stats_panel_source / "index.html").write_text("<html>stats</html>", encoding="utf-8")
            (stats_panel_source / "app.js").write_text("console.log('stats')", encoding="utf-8")

            manifest = prepare_pages_artifact(
                source,
                dest,
                keep_days=7,
                stats_panel_source=stats_panel_source,
            )

            self.assertEqual((dest / "stats" / "index.html").read_text(encoding="utf-8"), "<html>stats</html>")
            self.assertEqual((dest / "stats" / "app.js").read_text(encoding="utf-8"), "console.log('stats')")
            self.assertEqual(manifest["stats_panel"], "stats/index.html")

    def test_generates_content_json_from_latest_txt_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "output"
            dest = root / "public"

            (source / "2026-06-29" / "html").mkdir(parents=True)
            (source / "2026-06-29" / "txt").mkdir(parents=True)

            (source / "index.html").write_text("<html>latest</html>", encoding="utf-8")
            (source / "2026-06-29" / "html" / "16-04.html").write_text("<html>report</html>", encoding="utf-8")
            (source / "2026-06-29" / "txt" / "16-04.txt").write_text(
                "\n".join(
                    [
                        "douyin | 抖音",
                        "1. AI 工作流实践 [URL:https://www.douyin.com/video/1] [COVER:https://img.example.com/cover.jpg]",
                        "2. Vibe Coding 游戏开发 [URL:https://www.douyin.com/video/2]",
                        "",
                        "xiaohongshu | 小红书",
                        "1. Codex 使用体验 [URL:https://www.xiaohongshu.com/explore/1]",
                    ]
                ),
                encoding="utf-8",
            )

            manifest = prepare_pages_artifact(source, dest, keep_days=7, import_source=root / "missing-imports")

            content = json.loads((dest / "content.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["content_json"], "content.json")
            self.assertEqual(content["total"], 3)
            self.assertEqual(content["snapshot"]["date"], "2026-06-29")
            self.assertEqual(content["platforms"][0], {"id": "douyin", "name": "抖音", "count": 2})
            self.assertEqual(content["items"][0]["platform_id"], "douyin")
            self.assertEqual(content["items"][0]["platform_name"], "抖音")
            self.assertEqual(content["items"][0]["rank"], 1)
            self.assertEqual(content["items"][0]["title"], "AI 工作流实践")
            self.assertEqual(content["items"][0]["url"], "https://www.douyin.com/video/1")
            self.assertEqual(content["items"][0]["cover_url"], "https://img.example.com/cover.jpg")

    def test_content_json_keeps_only_douyin_and_xiaohongshu_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "output"
            dest = root / "public"

            (source / "2026-06-29" / "html").mkdir(parents=True)
            (source / "2026-06-29" / "txt").mkdir(parents=True)

            (source / "index.html").write_text("<html>latest</html>", encoding="utf-8")
            (source / "2026-06-29" / "html" / "16-04.html").write_text("<html>report</html>", encoding="utf-8")
            (source / "2026-06-29" / "txt" / "16-04.txt").write_text(
                "\n".join(
                    [
                        "sspai | 少数派",
                        "1. AI 工作流实践 [URL:https://sspai.com/post/1]",
                        "",
                        "douyin | 抖音",
                        "1. Vibe Coding 抖音案例 [URL:https://www.douyin.com/video/1]",
                        "",
                        "v2ex | V2EX",
                        "1. Codex 使用体验 [URL:https://www.v2ex.com/t/1]",
                    ]
                ),
                encoding="utf-8",
            )

            prepare_pages_artifact(source, dest, keep_days=7, import_source=root / "missing-imports")

            content = json.loads((dest / "content.json").read_text(encoding="utf-8"))
            self.assertEqual(content["total"], 1)
            self.assertEqual(content["platforms"], [{"id": "douyin", "name": "抖音", "count": 1}])
            self.assertEqual(content["items"][0]["platform_id"], "douyin")
            self.assertEqual(content["items"][0]["title"], "Vibe Coding 抖音案例")

    def test_merges_imported_douyin_search_content_before_hotlist_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "output"
            dest = root / "public"
            import_source = root / "imports"

            (source / "2026-06-29" / "html").mkdir(parents=True)
            (source / "2026-06-29" / "txt").mkdir(parents=True)
            import_source.mkdir()

            (source / "index.html").write_text("<html>latest</html>", encoding="utf-8")
            (source / "2026-06-29" / "html" / "16-04.html").write_text("<html>report</html>", encoding="utf-8")
            (source / "2026-06-29" / "txt" / "16-04.txt").write_text(
                "douyin | 抖音\n1. 普通热榜 [URL:https://www.douyin.com/hot/1]\n",
                encoding="utf-8",
            )
            (import_source / "douyin_vibecoding.csv").write_text(
                "\n".join(
                    [
                        "platform,title,url,author,description,published_at,likes,comments,shares,cover_url",
                        "douyin,VibeCoding大赏,https://www.douyin.com/video/1,作者,搜索描述,2026-06-15,100,,,https://img.example.com/douyin.jpg",
                    ]
                ),
                encoding="utf-8",
            )

            prepare_pages_artifact(source, dest, keep_days=7, import_source=import_source)

            content = json.loads((dest / "content.json").read_text(encoding="utf-8"))
            self.assertEqual(content["total"], 2)
            self.assertEqual(content["platforms"][0], {"id": "douyin-search", "name": "抖音搜索", "count": 1})
            self.assertEqual(content["items"][0]["source_type"], "search_import")
            self.assertEqual(content["items"][0]["platform_id"], "douyin-search")
            self.assertEqual(content["items"][0]["platform_name"], "抖音搜索")
            self.assertEqual(content["items"][0]["title"], "VibeCoding大赏")
            self.assertEqual(content["items"][0]["author"], "作者")
            self.assertEqual(content["items"][0]["published_at"], "2026-06-15")
            self.assertEqual(content["items"][0]["likes"], "100")
            self.assertEqual(content["items"][0]["cover_url"], "https://img.example.com/douyin.jpg")
            self.assertEqual(content["items"][1]["source_type"], "hotlist")

    def test_merges_topic_radar_imports_with_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "output"
            dest = root / "public"
            import_source = root / "imports"

            (source / "2026-06-29" / "html").mkdir(parents=True)
            (source / "2026-06-29" / "txt").mkdir(parents=True)
            import_source.mkdir()

            (source / "index.html").write_text("<html>latest</html>", encoding="utf-8")
            (source / "2026-06-29" / "html" / "16-04.html").write_text("<html>report</html>", encoding="utf-8")
            (source / "2026-06-29" / "txt" / "16-04.txt").write_text(
                "douyin | 抖音\n1. 普通热榜 [URL:https://www.douyin.com/hot/1]\n",
                encoding="utf-8",
            )
            (import_source / "00_vibecoding_case_radar.csv").write_text(
                "\n".join(
                    [
                        "platform,title,url,cover_url,author,published_at,like_count,comment_count,collect_count,share_count,hot_score,recent_hot_score,case_type,built_thing,tool_stack,target_audience,hook,content_value,risk_flag,description",
                        "douyin,AI 做作品集,https://www.douyin.com/video/1,https://img.example.com/douyin.jpg,作者,2026-06-15,100,2,3,4,900,450,真案例,网站、创意实验,Codex,设计师,几小时上线,有结果,平台活动内容,搜索描述",
                        "xiaohongshu,Codex 工作流,https://www.xiaohongshu.com/explore/1,https://img.example.com/xhs.jpg,博主,2026-06-14,80,1,2,3,700,300,教程,自动化流程,Codex,运营,完整流程,可复制,,小红书描述",
                    ]
                ),
                encoding="utf-8",
            )

            prepare_pages_artifact(source, dest, keep_days=7, import_source=import_source)

            content = json.loads((dest / "content.json").read_text(encoding="utf-8"))
            self.assertEqual(content["total"], 3)
            self.assertEqual(content["platforms"][0], {"id": "douyin-topic", "name": "抖音选题", "count": 1})
            self.assertEqual(content["platforms"][1], {"id": "xiaohongshu-topic", "name": "小红书选题", "count": 1})
            self.assertEqual(content["imports"]["total"], 2)

            douyin_item = content["items"][0]
            self.assertEqual(douyin_item["source_type"], "topic_import")
            self.assertEqual(douyin_item["platform_id"], "douyin-topic")
            self.assertEqual(douyin_item["platform_name"], "抖音选题")
            self.assertEqual(douyin_item["likes"], "100")
            self.assertEqual(douyin_item["comments"], "2")
            self.assertEqual(douyin_item["collects"], "3")
            self.assertEqual(douyin_item["shares"], "4")
            self.assertEqual(douyin_item["case_type"], "真案例")
            self.assertEqual(douyin_item["built_thing"], "网站、创意实验")
            self.assertEqual(douyin_item["tool_stack"], "Codex")
            self.assertEqual(douyin_item["target_audience"], "设计师")
            self.assertEqual(douyin_item["hook"], "几小时上线")
            self.assertEqual(douyin_item["content_value"], "有结果")
            self.assertEqual(douyin_item["risk_flag"], "平台活动内容")
            self.assertEqual(douyin_item["hot_score"], "900")
            self.assertEqual(douyin_item["recent_hot_score"], "450")

            xhs_item = content["items"][1]
            self.assertEqual(xhs_item["platform_id"], "xiaohongshu-topic")
            self.assertEqual(xhs_item["platform_name"], "小红书选题")
            self.assertEqual(xhs_item["cover_url"], "https://img.example.com/xhs.jpg")

    def test_skips_irrelevant_topic_import_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "output"
            dest = root / "public"
            import_source = root / "imports"

            (source / "2026-06-29" / "html").mkdir(parents=True)
            (source / "2026-06-29" / "txt").mkdir(parents=True)
            import_source.mkdir()

            (source / "index.html").write_text("<html>latest</html>", encoding="utf-8")
            (source / "2026-06-29" / "html" / "16-04.html").write_text("<html>report</html>", encoding="utf-8")
            (source / "2026-06-29" / "txt" / "16-04.txt").write_text("", encoding="utf-8")
            (import_source / "full_cases.csv").write_text(
                "\n".join(
                    [
                        "platform,title,url,case_type,built_thing,tool_stack,content_value,description",
                        "douyin,保留真案例,https://www.douyin.com/video/keep,真案例,网站,Codex,有结果,有结果",
                        "douyin,删掉无关,https://www.douyin.com/video/skip1,无关,,Codex,,无关内容",
                        "douyin,删掉观点,https://www.douyin.com/video/skip2,观点内容,,Codex,只有噱头,只有观点",
                        "xiaohongshu,删掉引流,https://www.xiaohongshu.com/explore/skip3,课程引流,,Codex,引流明显,课程引流",
                        "douyin,删掉空教程,https://www.douyin.com/video/skip4,教程,,Codex,可复刻,没有具体方向",
                        "douyin,删掉噱头测评,https://www.douyin.com/video/skip5,工具测评,工具,Codex,只有噱头,只有噱头",
                    ]
                ),
                encoding="utf-8",
            )

            prepare_pages_artifact(source, dest, keep_days=7, import_source=import_source)

            content = json.loads((dest / "content.json").read_text(encoding="utf-8"))
            self.assertEqual(content["imports"]["total"], 1)
            self.assertEqual(content["total"], 1)
            self.assertEqual(content["items"][0]["title"], "保留真案例")

    def test_copies_content_panel_assets_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "output"
            dest = root / "public"
            content_panel_source = root / "web" / "content-panel"

            source.mkdir()
            content_panel_source.mkdir(parents=True)

            (source / "index.html").write_text("<html>latest</html>", encoding="utf-8")
            (content_panel_source / "index.html").write_text("<html>content</html>", encoding="utf-8")
            (content_panel_source / "app.js").write_text("console.log('content')", encoding="utf-8")

            manifest = prepare_pages_artifact(
                source,
                dest,
                keep_days=7,
                content_panel_source=content_panel_source,
            )

            self.assertEqual((dest / "content" / "index.html").read_text(encoding="utf-8"), "<html>content</html>")
            self.assertEqual((dest / "content" / "app.js").read_text(encoding="utf-8"), "console.log('content')")
            self.assertEqual(manifest["content_panel"], "content/index.html")


if __name__ == "__main__":
    unittest.main()
