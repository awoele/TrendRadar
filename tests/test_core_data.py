import tempfile
import unittest
from pathlib import Path

from trendradar.core.data import save_titles_to_file


class CoreDataTests(unittest.TestCase):
    def test_save_titles_to_file_writes_cover_tag_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "titles.txt"

            save_titles_to_file(
                {
                    "bilibili": {
                        "AI 工具": {
                            "ranks": [1],
                            "url": "https://example.com/item",
                            "coverUrl": "https://img.example.com/cover.png",
                        }
                    }
                },
                {"bilibili": "哔哩哔哩"},
                [],
                str(output_path),
                lambda title: title,
            )

            self.assertIn(
                "1. AI 工具 [URL:https://example.com/item] [COVER:https://img.example.com/cover.png]",
                output_path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
