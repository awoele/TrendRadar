import unittest
from pathlib import Path


class ContentPanelAssetTests(unittest.TestCase):
    def test_platform_chips_are_clickable_filters(self):
        app_js = Path("web/content-panel/app.js").read_text(encoding="utf-8")

        self.assertIn('button.type = "button"', app_js)
        self.assertIn('data-platform-id', app_js)
        self.assertIn("setPlatformFilter", app_js)
        self.assertIn('dom.platformStrip.addEventListener("click"', app_js)

    def test_active_platform_chip_has_visible_state(self):
        styles = Path("web/content-panel/styles.css").read_text(encoding="utf-8")

        self.assertIn(".platform-chip.active", styles)
        self.assertIn("aria-pressed", Path("web/content-panel/app.js").read_text(encoding="utf-8"))

    def test_topic_metadata_renders_as_card_tags(self):
        app_js = Path("web/content-panel/app.js").read_text(encoding="utf-8")
        styles = Path("web/content-panel/styles.css").read_text(encoding="utf-8")

        self.assertIn("topicTags", app_js)
        self.assertIn("case_type", app_js)
        self.assertIn("tool_stack", app_js)
        self.assertIn("hook", app_js)
        self.assertIn("content-tags", app_js)
        self.assertIn(".content-tags", styles)

    def test_topic_filter_controls_match_radar_panel_dimensions(self):
        index_html = Path("web/content-panel/index.html").read_text(encoding="utf-8")
        app_js = Path("web/content-panel/app.js").read_text(encoding="utf-8")
        styles = Path("web/content-panel/styles.css").read_text(encoding="utf-8")

        for control_id in (
            "caseTypeSelect",
            "builtThingSelect",
            "toolStackSelect",
            "hookSelect",
            "contentValueSelect",
            "riskFlagSelect",
            "sortSelect",
        ):
            self.assertIn(control_id, index_html)
            self.assertIn(control_id, app_js)

        self.assertIn("populateTopicFilters", app_js)
        self.assertIn("topicFilterFields", app_js)
        self.assertIn("matchesTopicFilter", app_js)
        self.assertIn("sortItems", app_js)
        self.assertIn(".topic-filters", styles)

    def test_content_panel_defaults_to_newest_first_sorting(self):
        index_html = Path("web/content-panel/index.html").read_text(encoding="utf-8")
        app_js = Path("web/content-panel/app.js").read_text(encoding="utf-8")

        self.assertNotIn('value="default"', index_html)
        self.assertLess(index_html.index('value="published_at"'), index_html.index('value="hot_score"'))
        self.assertIn('sortBy: "published_at"', app_js)
        self.assertIn("compareNewestFirst", app_js)
        self.assertNotIn('if (state.sortBy === "default")', app_js)

    def test_content_panel_renders_collection_run_history(self):
        index_html = Path("web/content-panel/index.html").read_text(encoding="utf-8")
        app_js = Path("web/content-panel/app.js").read_text(encoding="utf-8")
        styles = Path("web/content-panel/styles.css").read_text(encoding="utf-8")

        self.assertIn("collectionRunList", index_html)
        self.assertIn("renderCollectionRuns", app_js)
        self.assertIn("collection_runs", app_js)
        self.assertIn(".collection-runs", styles)
        self.assertIn(".run-card", styles)

    def test_content_panel_opens_with_content_before_run_history(self):
        index_html = Path("web/content-panel/index.html").read_text(encoding="utf-8")
        styles = Path("web/content-panel/styles.css").read_text(encoding="utf-8")

        self.assertNotIn("summary-band", index_html)
        self.assertIn('<details class="advanced-filters"', index_html)
        self.assertIn('<details class="collection-runs"', index_html)
        self.assertLess(index_html.index("platformStrip"), index_html.index("contentList"))
        self.assertLess(index_html.index("contentList"), index_html.index("collectionRunList"))
        self.assertIn(".topbar.compact", styles)
        self.assertIn(".advanced-filters", styles)

    def test_panels_do_not_link_to_legacy_blue_report_home(self):
        panel_paths = (
            Path("web/content-panel/index.html"),
            Path("web/stats-panel/index.html"),
            Path("web/config-panel/index.html"),
        )

        for panel_path in panel_paths:
            with self.subTest(panel=str(panel_path)):
                html = panel_path.read_text(encoding="utf-8")
                self.assertNotIn('href="../index.html"', html)
                self.assertNotIn("打开最新报告", html)
                self.assertNotIn("查看热榜", html)
                self.assertNotIn("最近报告", html)

        stats_app = Path("web/stats-panel/app.js").read_text(encoding="utf-8")
        stats_css = Path("web/stats-panel/styles.css").read_text(encoding="utf-8")
        self.assertNotIn("report.path", stats_app)
        self.assertNotIn("reportRows", stats_app)
        self.assertNotIn(".report-item", stats_css)
        self.assertNotIn(".report-list", stats_css)

    def test_public_publish_does_not_run_legacy_report_crawler_or_services(self):
        workflow = Path(".github/workflows/free-pages.yml").read_text(encoding="utf-8")
        publish_script = Path("local-publish-free-pages.ps1").read_text(encoding="utf-8")
        collect_script = Path("local-collect-xhs-douyin.ps1").read_text(encoding="utf-8")

        self.assertNotIn("python -m trendradar", workflow)
        self.assertNotIn("Run crawler", workflow)
        self.assertIn("fetch-depth: 0", workflow)
        self.assertNotIn("local-run-once.ps1", publish_script)
        self.assertNotIn("local-serve-output.ps1", publish_script)
        self.assertNotIn("MCP", publish_script)
        self.assertIn("fetch_tikhub_douyin_search.py", collect_script)
        self.assertNotIn("fetch_hot_search_result", collect_script)
        self.assertNotIn("collect_authenticated.cjs", collect_script)
        self.assertIn("$KeywordLimit", collect_script)

    def test_xiaohongshu_collection_uses_skill_and_douyin_uses_tikhub_keyword_search(self):
        collect_script = Path("local-collect-xhs-douyin.ps1").read_text(encoding="utf-8")

        self.assertIn("scripts\\import_redfox_xhs.py", collect_script)
        self.assertIn("xiaohongshu-crawler", collect_script)
        self.assertIn("fetch_tikhub_douyin_search.py", collect_script)
        self.assertIn("tikhub_douyin_search_raw", collect_script)
        self.assertIn("Resolve-TikHubPublishTime", collect_script)
        self.assertIn("$tikhubPublishTime", collect_script)
        self.assertNotIn('"--platform", "both"', collect_script)
        self.assertIn("02_xhs_skill_vibecoding", collect_script)
        self.assertIn("03_douyin_tikhub_vibecoding", collect_script)

    def test_xiaohongshu_skill_path_is_derived_without_chinese_literal(self):
        collect_script = Path("local-collect-xhs-douyin.ps1").read_text(encoding="utf-8")

        self.assertNotIn(r"D:\Documents\热点库", collect_script)
        self.assertIn("$workspaceRoot = Split-Path -Parent $root", collect_script)
        self.assertIn("$defaultXhsSkillScript", collect_script)

    def test_config_panel_only_exposes_xhs_and_douyin_platforms(self):
        app_js = Path("web/config-panel/app.js").read_text(encoding="utf-8")
        index_html = Path("web/config-panel/index.html").read_text(encoding="utf-8")

        self.assertIn('{ id: "xiaohongshu", name: "小红书" }', app_js)
        self.assertIn('{ id: "douyin", name: "抖音" }', app_js)
        for removed_platform in ("weibo", "zhihu", "bilibili", "toutiao", "github-trending-today"):
            self.assertNotIn(f'id: "{removed_platform}"', app_js)

        self.assertNotIn("customPlatformId", app_js)
        self.assertNotIn("customPlatformId", index_html)
        self.assertNotIn("报告模式", index_html)


if __name__ == "__main__":
    unittest.main()
