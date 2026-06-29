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


if __name__ == "__main__":
    unittest.main()
