import unittest
import tempfile
from pathlib import Path

from scripts.prepare_pages_artifact import _collection_runs, _imported_search_content


class DouyinFavoritesCollectorTests(unittest.TestCase):
    def test_collector_targets_authenticated_favorites_and_standard_columns(self):
        script = Path("scripts/collect_douyin_favorites.cjs").read_text(encoding="utf-8")

        self.assertIn("SOURCE_NAME = \"douyin:favorites\"", script)
        self.assertIn("listcollection", script)
        self.assertIn(".auth/platform-profile", script)
        self.assertIn("\"platform\"", script)
        self.assertIn("\"title\"", script)
        self.assertIn("\"url\"", script)
        self.assertIn("\"cover_url\"", script)
        self.assertIn("\"like_count\"", script)
        self.assertIn("\"source\"", script)
        self.assertNotIn("TIKHUB_API_KEY", script)
        self.assertNotIn("fetch_hot_search_result", script)

    def test_favorite_rows_enter_the_panel_as_douyin_favorites(self):
        import_dir = Path(self.id().replace(".", "_"))
        import_dir.mkdir(exist_ok=True)
        try:
            csv_path = import_dir / "04_douyin_favorites_2026-06-30.csv"
            csv_path.write_text(
                "\ufeff"
                + "\n".join(
                    [
                        "platform,title,url,cover_url,author,published_at,like_count,comment_count,collect_count,share_count,description,source",
                        "douyin,Favorite vibe coding,https://www.douyin.com/video/99,https://img.example.com/favorite.jpg,Creator,2026-06-30,10,2,3,4,Collected description,douyin:favorites",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            content = _imported_search_content(import_dir)
        finally:
            for child in import_dir.glob("*"):
                child.unlink()
            import_dir.rmdir()

        self.assertEqual(content["platforms"], [{"id": "douyin-favorites", "name": "抖音收藏", "count": 1}])
        self.assertEqual(content["items"][0]["platform_id"], "douyin-favorites")
        self.assertEqual(content["items"][0]["platform_name"], "抖音收藏")
        self.assertEqual(content["items"][0]["source_type"], "favorite_import")
        self.assertEqual(content["items"][0]["source"], "douyin:favorites")

    def test_favorite_collection_run_is_separate_from_douyin_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            import_dir = Path(tmp)
            (import_dir / "04_douyin_favorites_2026-06-30.csv").write_text(
                "\ufeff"
                + "\n".join(
                    [
                        "platform,title,url,published_at,source",
                        "douyin,Favorite one,https://www.douyin.com/video/1,2026-06-30,douyin:favorites",
                        "douyin,Favorite two,https://www.douyin.com/video/2,2026-06-30,douyin:favorites",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            runs = _collection_runs(import_dir)

        self.assertEqual(runs[0]["platforms"], [{"id": "douyin-favorites", "name": "抖音收藏", "count": 2}])
        self.assertEqual(runs[0]["sources"], ["douyin:favorites"])


if __name__ == "__main__":
    unittest.main()
