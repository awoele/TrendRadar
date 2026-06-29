import argparse
import csv
import html
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _date_dir(path: Path):
    try:
        return datetime.strptime(path.name, "%Y-%m-%d").date()
    except ValueError:
        return None


def _copy_file(source: Path, dest: Path) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return {
        "path": dest.as_posix(),
        "bytes": dest.stat().st_size,
    }


def _write_content_home(dest: Path) -> None:
    dest.write_text(
        """<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="0; url=content/">
    <title>TrendRadar 内容</title>
    <link rel="canonical" href="content/">
  </head>
  <body>
    <script>
      window.location.replace("content/");
    </script>
    <p><a href="content/">打开内容面板</a></p>
  </body>
</html>
""",
        encoding="utf-8",
    )


def _clean_html_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _first_nonempty(row: dict, field_names: tuple) -> str:
    for field_name in field_names:
        value = (row.get(field_name) or "").strip()
        if value:
            return value
    return ""


def _import_platform(platform: str, is_topic_import: bool) -> tuple:
    platform_names = {
        "douyin": "抖音",
        "xiaohongshu": "小红书",
    }
    base_name = platform_names.get(platform, platform)
    suffix = "topic" if is_topic_import else "search"
    suffix_name = "选题" if is_topic_import else "搜索"
    return f"{platform}-{suffix}", f"{base_name}{suffix_name}"


def _is_topic_import(row: dict) -> bool:
    return any(
        (row.get(field_name) or "").strip()
        for field_name in (
            "case_type",
            "built_thing",
            "tool_stack",
            "target_audience",
            "hook",
            "content_value",
            "risk_flag",
            "hot_score",
            "recent_hot_score",
            "category_label",
        )
    )


def _topic_labels(row: dict, key: str) -> list[str]:
    return [value.strip() for value in re.split(r"[、,，;；|]", row.get(key) or "") if value.strip()]


def _is_relevant_topic(row: dict) -> bool:
    case_type = (row.get("case_type") or "").strip()
    built_thing = _topic_labels(row, "built_thing")
    content_value = _topic_labels(row, "content_value")

    if case_type in {"无关", "观点内容", "课程引流"}:
        return False
    if case_type in {"真案例", "失败复盘"}:
        return True
    if case_type == "教程":
        return bool(built_thing)
    if case_type == "工具测评":
        return bool(built_thing and "只有噱头" not in content_value)
    return False


def _parse_item_payload(value: str) -> tuple:
    fields = {}

    def collect(match: re.Match) -> str:
        fields[match.group(1).lower()] = match.group(2).strip()
        return ""

    title = re.sub(r"\s+\[([A-Z_]+):(.*?)\]", collect, value).strip()
    return title, fields


def _parse_metric(html_text: str, label: str):
    expression = re.compile(
        rf'<span\s+class="info-label">\s*{re.escape(label)}\s*</span>\s*'
        r'<span\s+class="info-value">\s*([\d,]+)',
        re.IGNORECASE,
    )
    match = expression.search(html_text)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def _word_group_blocks(html_text: str):
    starts = [
        match.start()
        for match in re.finditer(r'<div\s+class="word-group"\s*>', html_text)
    ]
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(html_text)
        yield html_text[start:end]


def _parse_latest_report_stats(html_path: Path) -> dict:
    html_text = html_path.read_text(encoding="utf-8", errors="ignore")
    keywords = []
    matched_by_platform = {}

    for block in _word_group_blocks(html_text):
        name_match = re.search(
            r'<div\s+class="word-name">\s*(.*?)\s*</div>',
            block,
            re.DOTALL | re.IGNORECASE,
        )
        count_match = re.search(
            r'<div\s+class="word-count[^"]*">\s*([\d,]+)',
            block,
            re.DOTALL | re.IGNORECASE,
        )
        if not name_match:
            continue

        source_names = [
            _clean_html_text(item)
            for item in re.findall(
                r'<span\s+class="source-name">\s*(.*?)\s*</span>',
                block,
                re.DOTALL | re.IGNORECASE,
            )
        ]
        source_names = [name for name in source_names if name]
        source_counts = {}
        for source_name in source_names:
            source_counts[source_name] = source_counts.get(source_name, 0) + 1
            matched_by_platform[source_name] = (
                matched_by_platform.get(source_name, 0) + 1
            )

        matched = (
            int(count_match.group(1).replace(",", ""))
            if count_match
            else len(source_names)
        )
        keywords.append(
            {
                "name": _clean_html_text(name_match.group(1)),
                "matched": matched,
                "platforms": [
                    {"name": name, "matched": count}
                    for name, count in sorted(
                        source_counts.items(), key=lambda item: (-item[1], item[0])
                    )
                ],
            }
        )

    keywords.sort(key=lambda item: (-item["matched"], item["name"].lower()))
    failed_platforms = [
        _clean_html_text(item)
        for item in re.findall(
            r'<li\s+class="error-item">\s*(.*?)\s*</li>',
            html_text,
            re.DOTALL | re.IGNORECASE,
        )
    ]

    return {
        "crawled_titles": _parse_metric(html_text, "新闻总数"),
        "matched_titles": _parse_metric(html_text, "热点新闻"),
        "keywords": keywords,
        "matched_by_platform": matched_by_platform,
        "failed_platforms": [item for item in failed_platforms if item],
    }


def _latest_txt_snapshot(source: Path):
    candidates = []
    for child in source.iterdir():
        if not child.is_dir():
            continue
        parsed = _date_dir(child)
        if not parsed:
            continue
        txt_dir = child / "txt"
        if not txt_dir.exists():
            continue
        for txt_file in txt_dir.glob("*.txt"):
            candidates.append((parsed, txt_file.stem, txt_file))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (item[0], item[1]), reverse=True)[0][2]


def _parse_txt_platform_counts(txt_path: Path) -> list:
    if not txt_path or not txt_path.exists():
        return []

    platforms = []
    current = None
    header_expression = re.compile(r"^([A-Za-z0-9._-]+)\s*\|\s*(.+)$")
    item_expression = re.compile(r"^\d+\.")

    for raw_line in txt_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        header = header_expression.match(line)
        if header:
            current = {
                "id": header.group(1).strip(),
                "name": header.group(2).strip(),
                "crawled": 0,
                "matched": 0,
            }
            platforms.append(current)
            continue
        if current and item_expression.match(line):
            current["crawled"] += 1

    return platforms


def _parse_txt_snapshot_content(txt_path: Path) -> dict:
    if not txt_path or not txt_path.exists():
        return {
            "snapshot": None,
            "total": 0,
            "platforms": [],
            "items": [],
        }

    snapshot_date = txt_path.parent.parent.name
    snapshot_time = txt_path.stem
    platforms = []
    items = []
    current = None
    header_expression = re.compile(r"^([A-Za-z0-9._-]+)\s*\|\s*(.+)$")
    item_expression = re.compile(r"^(\d+)\.\s+(.*)$")

    for raw_line in txt_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        header = header_expression.match(line)
        if header:
            current = {
                "id": header.group(1).strip(),
                "name": header.group(2).strip(),
                "count": 0,
            }
            platforms.append(current)
            continue

        item = item_expression.match(line)
        if current and item:
            title, fields = _parse_item_payload(item.group(2).strip())
            url = fields.get("url", "")
            cover_url = fields.get("cover", "")
            current["count"] += 1
            items.append(
                {
                    "platform_id": current["id"],
                    "platform_name": current["name"],
                    "rank": int(item.group(1)),
                    "title": title,
                    "url": url,
                    "cover_url": cover_url,
                    "source_type": "hotlist",
                }
            )

    return {
        "snapshot": {
            "date": snapshot_date,
            "time": snapshot_time,
            "path": txt_path.as_posix(),
        },
        "total": len(items),
        "platforms": platforms,
        "items": items,
    }


def _imported_search_content(import_source: Path) -> dict:
    if not import_source.exists():
        return {
            "platforms": [],
            "items": [],
        }

    platforms = {}
    items = []
    seen_urls = set()

    for csv_file in sorted(import_source.glob("*.csv")):
        with csv_file.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                platform = (row.get("platform") or "").strip().lower()
                if platform not in {"douyin", "xiaohongshu"}:
                    continue

                title = (row.get("title") or "").strip()
                url = (row.get("url") or "").strip()
                if not title or not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                is_topic_import = _is_topic_import(row)
                if is_topic_import and not _is_relevant_topic(row):
                    continue

                platform_id, platform_name = _import_platform(platform, is_topic_import)
                platforms.setdefault(
                    platform_id,
                    {
                        "id": platform_id,
                        "name": platform_name,
                        "count": 0,
                    },
                )
                platforms[platform_id]["count"] += 1
                items.append(
                    {
                        "platform_id": platform_id,
                        "platform_name": platform_name,
                        "rank": None,
                        "title": title,
                        "url": url,
                        "cover_url": _first_nonempty(
                            row,
                            (
                                "cover_url",
                                "cover",
                                "image_url",
                                "image",
                                "thumbnail_url",
                                "thumbnail",
                                "poster_url",
                                "poster",
                            ),
                        ),
                        "source_type": "topic_import" if is_topic_import else "search_import",
                        "author": (row.get("author") or "").strip(),
                        "description": (row.get("description") or "").strip(),
                        "published_at": (row.get("published_at") or "").strip(),
                        "likes": _first_nonempty(row, ("likes", "like_count")),
                        "comments": _first_nonempty(row, ("comments", "comment_count")),
                        "collects": _first_nonempty(row, ("collects", "collect_count")),
                        "shares": _first_nonempty(row, ("shares", "share_count")),
                        "case_type": (row.get("case_type") or "").strip(),
                        "built_thing": (row.get("built_thing") or "").strip(),
                        "tool_stack": (row.get("tool_stack") or row.get("tools") or "").strip(),
                        "target_audience": (row.get("target_audience") or row.get("audience") or "").strip(),
                        "hook": (row.get("hook") or "").strip(),
                        "content_value": (row.get("content_value") or "").strip(),
                        "risk_flag": (row.get("risk_flag") or "").strip(),
                        "category_label": (row.get("category_label") or "").strip(),
                        "hot_score": (row.get("hot_score") or "").strip(),
                        "recent_hot_score": (row.get("recent_hot_score") or "").strip(),
                    }
                )

    return {
        "platforms": list(platforms.values()),
        "items": items,
    }


def _merge_platform_counts(*platform_lists: list) -> list:
    merged = {}
    for platform_list in platform_lists:
        for platform in platform_list:
            platform_id = platform["id"]
            merged.setdefault(
                platform_id,
                {
                    "id": platform_id,
                    "name": platform.get("name") or platform_id,
                    "count": 0,
                },
            )
            merged[platform_id]["count"] += int(platform.get("count", 0) or 0)
    return list(merged.values())


def _is_primary_content_platform(platform_id: str) -> bool:
    return platform_id in {
        "douyin-topic",
        "xiaohongshu-topic",
        "douyin-search",
        "xiaohongshu-search",
    }


def _filter_primary_content(content: dict) -> dict:
    items = [
        item
        for item in content.get("items", [])
        if _is_primary_content_platform(item.get("platform_id") or "")
    ]
    platforms = [
        platform
        for platform in content.get("platforms", [])
        if _is_primary_content_platform(platform.get("id") or "")
    ]
    return {
        **content,
        "total": len(items),
        "platforms": platforms,
        "items": items,
    }


def _build_public_content(source: Path, import_source: Path = Path("data/imports")) -> dict:
    content = _filter_primary_content(_parse_txt_snapshot_content(_latest_txt_snapshot(source)))
    imported = _imported_search_content(Path(import_source))
    content["items"] = imported["items"] + content["items"]
    content["platforms"] = _merge_platform_counts(imported["platforms"], content["platforms"])
    content["total"] = len(content["items"])
    content["generated_at"] = (
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    content["imports"] = {
        "total": len(imported["items"]),
        "platforms": imported["platforms"],
    }
    return content


def _build_public_stats(source: Path, reports: list) -> dict:
    latest_stats = _parse_latest_report_stats(source / "index.html")
    platforms = _parse_txt_platform_counts(_latest_txt_snapshot(source))
    known_platforms = {}

    for platform in platforms:
        known_platforms[platform["id"]] = platform
        known_platforms[platform["name"]] = platform

    for platform_name, matched in latest_stats["matched_by_platform"].items():
        platform = known_platforms.get(platform_name)
        if platform is None:
            platform = {
                "id": platform_name,
                "name": platform_name,
                "crawled": 0,
                "matched": 0,
            }
            platforms.append(platform)
            known_platforms[platform_name] = platform
        platform["matched"] += matched

    crawled_titles = latest_stats["crawled_titles"]
    if crawled_titles is None:
        crawled_titles = sum(platform["crawled"] for platform in platforms)

    matched_titles = latest_stats["matched_titles"]
    if matched_titles is None:
        matched_titles = sum(keyword["matched"] for keyword in latest_stats["keywords"])

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "latest_report": {
            "path": "index.html",
            "title": "latest",
        },
        "totals": {
            "reports": len(reports),
            "crawled_titles": crawled_titles,
            "matched_titles": matched_titles,
            "failed_platforms": len(latest_stats["failed_platforms"]),
        },
        "platforms": platforms,
        "keywords": latest_stats["keywords"],
        "failed_platforms": latest_stats["failed_platforms"],
        "reports": reports,
    }


def prepare_pages_artifact(
    source: Path,
    dest: Path,
    keep_days: int = 7,
    panel_source: Path = Path("web/config-panel"),
    stats_panel_source: Path = Path("web/stats-panel"),
    content_panel_source: Path = Path("web/content-panel"),
    import_source: Path = Path("data/imports"),
) -> dict:
    source = Path(source)
    dest = Path(dest)
    panel_source = Path(panel_source)
    stats_panel_source = Path(stats_panel_source)
    content_panel_source = Path(content_panel_source)
    import_source = Path(import_source)

    if not (source / "index.html").exists():
        raise FileNotFoundError(f"Missing public report: {source / 'index.html'}")

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    _write_content_home(dest / "index.html")
    (dest / ".nojekyll").write_text("", encoding="utf-8")
    config_panel = None
    stats_panel = None
    content_panel = None

    if panel_source.exists():
        panel_dest = dest / "config"
        shutil.copytree(panel_source, panel_dest, dirs_exist_ok=True)
        if (panel_dest / "index.html").exists():
            config_panel = "config/index.html"

    if stats_panel_source.exists():
        stats_panel_dest = dest / "stats"
        shutil.copytree(stats_panel_source, stats_panel_dest, dirs_exist_ok=True)
        if (stats_panel_dest / "index.html").exists():
            stats_panel = "stats/index.html"

    if content_panel_source.exists():
        content_panel_dest = dest / "content"
        shutil.copytree(content_panel_source, content_panel_dest, dirs_exist_ok=True)
        if (content_panel_dest / "index.html").exists():
            content_panel = "content/index.html"

    dated_dirs = []
    for child in source.iterdir():
        if not child.is_dir():
            continue
        parsed = _date_dir(child)
        if parsed:
            dated_dirs.append((parsed, child))

    cutoff = None
    if dated_dirs:
        latest_date = max(item[0] for item in dated_dirs)
        cutoff = latest_date - timedelta(days=max(keep_days - 1, 0))

    reports = []
    for report_date, date_dir in sorted(dated_dirs, reverse=True):
        if cutoff and report_date < cutoff:
            continue

        html_dir = date_dir / "html"
        if not html_dir.exists():
            continue

        for html_file in sorted(html_dir.glob("*.html")):
            relative_dest = Path("reports") / date_dir.name / html_file.name
            copied = _copy_file(html_file, dest / relative_dest)
            reports.append(
                {
                    "date": date_dir.name,
                    "title": html_file.stem,
                    "path": relative_dest.as_posix(),
                    "bytes": copied["bytes"],
                }
            )

    stats = _build_public_stats(source, reports)
    (dest / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    content = _build_public_content(source, import_source)
    (dest / "content.json").write_text(
        json.dumps(content, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    manifest = {
        "latest": "index.html",
        "reports": reports,
        "keep_days": keep_days,
        "stats_json": "stats.json",
        "content_json": "content.json",
    }
    if config_panel:
        manifest["config_panel"] = config_panel
    if stats_panel:
        manifest["stats_panel"] = stats_panel
    if content_panel:
        manifest["content_panel"] = content_panel
    (dest / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare public GitHub Pages artifact.")
    parser.add_argument("--source", default="output", type=Path)
    parser.add_argument("--dest", default="public", type=Path)
    parser.add_argument("--keep-days", default=7, type=int)
    args = parser.parse_args()

    manifest = prepare_pages_artifact(args.source, args.dest, args.keep_days)
    print(f"Prepared {len(manifest['reports'])} reports in {args.dest}")


if __name__ == "__main__":
    main()
