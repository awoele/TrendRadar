import json
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_pages_artifact import prepare_pages_artifact


class PreparePagesArtifactTests(unittest.TestCase):
    def test_copies_index_recent_html_and_manifest(self):
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

            manifest = prepare_pages_artifact(source, dest, keep_days=7)

            self.assertEqual((dest / "index.html").read_text(encoding="utf-8"), "<html>latest</html>")
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

            manifest = prepare_pages_artifact(source, dest, keep_days=7)

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


if __name__ == "__main__":
    unittest.main()
