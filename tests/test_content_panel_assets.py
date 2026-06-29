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


if __name__ == "__main__":
    unittest.main()
