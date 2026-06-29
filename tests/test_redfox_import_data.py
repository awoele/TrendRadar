import csv
import unittest
from datetime import date
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

    def test_redfox_halfmonth_import_is_tagged_and_cover_enriched(self):
        path = Path("data/imports/01_redfox_xhs_vibecoding_2026-06-15_2026-06-29.csv")
        self.assertTrue(path.exists(), "RedFox 半月小红书导入文件不存在")

        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))

        self.assertGreaterEqual(len(rows), 100)
        required_fields = {
            "platform",
            "title",
            "url",
            "cover_url",
            "published_at",
            "case_type",
            "built_thing",
            "tool_stack",
            "hook",
            "hot_score",
            "recent_hot_score",
            "source",
        }
        self.assertTrue(required_fields.issubset(rows[0].keys()))

        start = date.fromisoformat("2026-06-15")
        end = date.fromisoformat("2026-06-29")
        for row in rows:
            self.assertEqual(row.get("platform"), "xiaohongshu")
            self.assertTrue(row.get("case_type"))
            self.assertTrue(row.get("built_thing") or row.get("tool_stack") or row.get("hook"))
            self.assertTrue(row.get("cover_url"))
            self.assertTrue((row.get("cover_url") or "").startswith("https://"))
            self.assertTrue((row.get("source") or "").startswith("redfox:xiaohongshu-crawler:"))
            published = date.fromisoformat(row["published_at"])
            self.assertGreaterEqual(published, start)
            self.assertLessEqual(published, end)

    def test_redfox_halfmonth_import_excludes_generic_ai_creative_topics(self):
        path = Path("data/imports/01_redfox_xhs_vibecoding_2026-06-15_2026-06-29.csv")

        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))

        excluded_titles = {
            "30秒直出！10种照片转风格插画｜附提示词",
            "邪修做3D设计？😈Y2K审美动态海报教程！",
        }
        titles = {row["title"] for row in rows}
        self.assertFalse(excluded_titles & titles)

        generic_terms = ("插画", "画图", "生图", "动态海报", "照片转", "纹样", "紫砂壶")
        strong_terms = (
            "vibecoding",
            "vibe coding",
            "codex",
            "cursor",
            "claude code",
            "ai编程",
            "ai 编程",
            "零代码",
            "不会代码",
            "写代码",
            "开发",
            "网站",
            "小程序",
            "插件",
            "自动化",
            "工作流",
            "agent",
            "智能体",
            "mcp",
            "dify",
            "coze",
            "n8n",
        )
        generic_without_strong_signal = []
        for row in rows:
            text = " ".join(
                [
                    row.get("title", ""),
                    row.get("description", ""),
                    row.get("built_thing", ""),
                    row.get("tool_stack", ""),
                ]
            ).lower()
            if any(term.lower() in text for term in generic_terms) and not any(
                term.lower() in text for term in strong_terms
            ):
                generic_without_strong_signal.append(row["title"])

        self.assertEqual(generic_without_strong_signal, [])

    def test_redfox_halfmonth_import_requires_raw_vibecoding_signal(self):
        path = Path("data/imports/01_redfox_xhs_vibecoding_2026-06-15_2026-06-29.csv")

        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))

        raw_signal_terms = (
            "vibecoding",
            "vibe coding",
            "codex",
            "cursor",
            "claude code",
            "ai coding",
            "ai编程",
            "ai 编程",
            "零代码",
            "不会代码",
            "写代码",
            "代码",
            "编程",
            "开发",
            "上线",
            "网站",
            "网页",
            "小程序",
            "app",
            "应用",
            "插件",
            "软件",
            "系统",
            "产品",
            "saas",
            "mvp",
            "agent",
            "智能体",
            "工作流",
            "自动化",
            "mcp",
            "dify",
            "coze",
            "扣子",
            "n8n",
            "github",
            "api",
            "独立开发",
        )
        missing_raw_signal = []
        for row in rows:
            raw_text = " ".join(
                [
                    row.get("title", ""),
                    row.get("description", ""),
                    row.get("tool_stack", ""),
                ]
            ).lower()
            if not any(term.lower() in raw_text for term in raw_signal_terms):
                missing_raw_signal.append(row["title"])

        self.assertEqual(missing_raw_signal, [])

    def test_redfox_halfmonth_import_excludes_news_finance_and_ticket_noise(self):
        path = Path("data/imports/01_redfox_xhs_vibecoding_2026-06-15_2026-06-29.csv")

        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))

        blocked_titles = {
            "BW外国人不用抢随便买票是吧？",
            "想入SpaceX？先听华尔街大佬怎么说",
            "SpaceX 确定 600 亿美元收购 CURSOR",
            "6月17日美股收益早报",
            "SpaceX宣布600亿收购Cursor、周二期权来袭",
            "GPT-5.6要上了？",
            "大学电脑怎么选⁉️华硕 a 豆/无畏轻薄本合集",
            "💻 四年不换的全能本，大一新生开学答案 📚",
        }
        titles = {row["title"] for row in rows}
        self.assertFalse(blocked_titles & titles)

    def test_redfox_halfmonth_import_excludes_brand_lifestyle_and_design_noise(self):
        path = Path("data/imports/01_redfox_xhs_vibecoding_2026-06-15_2026-06-29.csv")

        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))

        blocked_titles = {
            "角色故事板+导演台，让AI视频抽卡效率拉满",
            "6大字体提示词分享🔥howto早下班2小时❗️",
            "用 AI 修壁画做纹样造紫砂壶，大学生真敢想",
            "右滑一下，清爽版支付宝来了！",
            "《鸿蒙脑洞大开麦》看完我愣了很久",
            "第一批觉醒的家长，早已让孩子主动驾驭AI了",
            "APP 独家限免，先到先得",
            "鸿蒙真的“不够年轻”吗 我在HDC看到了另一面",
            "一张 3090 Ti，入选 SIGGRAPH 2026！",
            "外贸找工作先混进去再学！",
            "盲人女孩北漂14年：剪视频做运营，独立自由",
            "安利一款AI神器！打工牛马秒变自动化大神！",
            "一个合格设计师的设计工具都有哪些",
        }
        titles = {row["title"] for row in rows}
        self.assertFalse(blocked_titles & titles)

        blocked_fragments = (
            ("grok", "成人内容生成"),
            ("ai视频", "抽卡"),
            ("hdc2026", "鸿蒙"),
            ("支付宝", "邀测"),
            ("外贸实习", "投简历"),
            ("ui/ux 设计师工具学习指南", "figma 是海内外通用标准"),
        )
        leaked = []
        for row in rows:
            text = " ".join(
                [
                    row.get("title", ""),
                    row.get("description", ""),
                    row.get("built_thing", ""),
                    row.get("tool_stack", ""),
                ]
            ).lower()
            for fragments in blocked_fragments:
                if all(fragment.lower() in text for fragment in fragments):
                    leaked.append(row["title"] or row.get("url", ""))

        self.assertEqual(leaked, [])


if __name__ == "__main__":
    unittest.main()
