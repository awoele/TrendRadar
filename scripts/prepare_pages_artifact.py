import argparse
import csv
import html
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
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


def _import_platform(platform: str, is_topic_import: bool, source: str = "") -> tuple:
    if source == "douyin:favorites":
        return "douyin-favorites", "\u6296\u97f3\u6536\u85cf"

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


def _is_pronunciation_noise(row: dict) -> bool:
    text = " ".join(
        (row.get(field_name) or "")
        for field_name in ("title", "description", "content_value", "hook")
    ).lower()
    return any(
        pattern in text
        for pattern in (
            "英语发音",
            "发音怎么区分",
            "发音区别",
        )
    )


def _is_relevant_topic(row: dict) -> bool:
    if _is_pronunciation_noise(row):
        return False

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
    if not source.exists():
        return None

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
            "audit": {
                "raw_rows": 0,
                "included_rows": 0,
                "duplicate_urls": 0,
                "missing_required": 0,
                "unsupported_platform": 0,
                "excluded_source": 0,
                "irrelevant_topic": 0,
            },
        }

    platforms = {}
    items = []
    seen_urls = set()
    audit = {
        "raw_rows": 0,
        "included_rows": 0,
        "duplicate_urls": 0,
        "missing_required": 0,
        "unsupported_platform": 0,
        "excluded_source": 0,
        "irrelevant_topic": 0,
    }

    for csv_file in sorted(import_source.glob("*.csv")):
        if _is_smoke_import(csv_file):
            continue
        with csv_file.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                audit["raw_rows"] += 1
                platform = (row.get("platform") or "").strip().lower()
                if platform not in {"douyin", "xiaohongshu"}:
                    audit["unsupported_platform"] += 1
                    continue

                title = (row.get("title") or "").strip()
                url = (row.get("url") or "").strip()
                if not title or not url:
                    audit["missing_required"] += 1
                    continue

                source = (row.get("source") or "").strip()
                if source == "tikhub:douyin_hot_search":
                    audit["excluded_source"] += 1
                    continue

                is_topic_import = _is_topic_import(row)
                if is_topic_import and not _is_relevant_topic(row):
                    audit["irrelevant_topic"] += 1
                    continue

                if url in seen_urls:
                    audit["duplicate_urls"] += 1
                    continue
                seen_urls.add(url)

                platform_id, platform_name = _import_platform(platform, is_topic_import, source)
                source_type = (
                    "favorite_import"
                    if source == "douyin:favorites"
                    else "topic_import"
                    if is_topic_import
                    else "search_import"
                )
                platforms.setdefault(
                    platform_id,
                    {
                        "id": platform_id,
                        "name": platform_name,
                        "count": 0,
                    },
                )
                platforms[platform_id]["count"] += 1
                audit["included_rows"] += 1
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
                        "source_type": source_type,
                        "author": (row.get("author") or "").strip(),
                        "description": (row.get("description") or "").strip(),
                        "source": source,
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
        "audit": audit,
    }


def _collection_window_from_name(file_name: str) -> tuple[str, str]:
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", file_name)
    if len(dates) >= 2:
        return dates[-2], dates[-1]
    if len(dates) == 1:
        return dates[0], dates[0]
    return "", ""


def _is_smoke_import(path: Path) -> bool:
    return "smoke" in path.stem.lower()


def _collection_platform_name(platform: str) -> str:
    return {
        "douyin": "抖音",
        "douyin-favorites": "抖音收藏",
        "xiaohongshu": "小红书",
    }.get(platform, platform or "unknown")


def _csv_updated_at(path: Path) -> str:
    git_value = _git_file_updated_at(path)
    if git_value:
        return git_value
    return (
        datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _git_file_updated_at(path: Path) -> str:
    root = Path(__file__).resolve().parents[1]
    try:
        relative_path = path.resolve().relative_to(root.resolve())
    except ValueError:
        return ""

    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", relative_path.as_posix()],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""

    value = result.stdout.strip()
    if not value:
        return ""
    return value.replace("+00:00", "Z")


def _collection_runs(import_source: Path) -> list[dict]:
    if not import_source.exists():
        return []

    runs = []
    for csv_file in sorted(import_source.glob("*.csv")):
        if _is_smoke_import(csv_file):
            continue
        row_count = 0
        platform_counts = {}
        keywords = set()
        sources = set()
        published_dates = []

        with csv_file.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                row_count += 1
                platform = (row.get("platform") or "").strip().lower()
                source = (row.get("source") or "").strip()
                if source == "douyin:favorites":
                    platform = "douyin-favorites"
                if platform:
                    platform_counts[platform] = platform_counts.get(platform, 0) + 1

                keyword = (row.get("keyword") or "").strip()
                if keyword:
                    keywords.add(keyword)

                if source:
                    sources.add(source)

                published_at = (row.get("published_at") or "").strip()[:10]
                if re.match(r"\d{4}-\d{2}-\d{2}$", published_at):
                    published_dates.append(published_at)

        if row_count == 0 and "douyin_favorites" in csv_file.stem.lower():
            platform_counts.setdefault("douyin", 0)
            sources.add("douyin:favorites")

        start_date, end_date = _collection_window_from_name(csv_file.name)
        if not start_date and published_dates:
            start_date = min(published_dates)
            end_date = max(published_dates)

        runs.append(
            {
                "file": csv_file.name,
                "start_date": start_date,
                "end_date": end_date,
                "updated_at": _csv_updated_at(csv_file),
                "row_count": row_count,
                "keyword_count": len(keywords),
                "keywords": sorted(keywords, key=str.lower),
                "platforms": [
                    {
                        "id": platform,
                        "name": _collection_platform_name(platform),
                        "count": count,
                    }
                    for platform, count in sorted(
                        platform_counts.items(), key=lambda item: (-item[1], item[0])
                    )
                ],
                "sources": sorted(sources, key=str.lower),
            }
        )

    return sorted(
        runs,
        key=lambda run: (
            run.get("end_date") or "",
            run.get("updated_at") or "",
            run.get("file") or "",
        ),
        reverse=True,
    )


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
        "douyin-favorites",
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


def _dedupe_public_content(content: dict) -> dict:
    items = []
    seen_urls = set()
    merged_duplicate_urls = 0
    missing_url_items = 0

    for item in content.get("items", []):
        url = (item.get("url") or "").strip()
        if url:
            if url in seen_urls:
                merged_duplicate_urls += 1
                continue
            seen_urls.add(url)
        else:
            missing_url_items += 1
        items.append(item)

    platforms = {}
    for item in items:
        platform_id = item.get("platform_id") or item.get("platform_name") or "unknown"
        platforms.setdefault(
            platform_id,
            {
                "id": platform_id,
                "name": item.get("platform_name") or platform_id or "未知平台",
                "count": 0,
            },
        )
        platforms[platform_id]["count"] += 1

    return {
        **content,
        "total": len(items),
        "platforms": list(platforms.values()),
        "items": items,
        "deduplication": {
            "merged_duplicate_urls": merged_duplicate_urls,
            "url_items": len(items) - missing_url_items,
            "missing_url_items": missing_url_items,
        },
    }


def _build_public_content(source: Path, import_source: Path = Path("data/imports")) -> dict:
    import_source = Path(import_source)
    content = _filter_primary_content(_parse_txt_snapshot_content(_latest_txt_snapshot(source)))
    imported = _imported_search_content(import_source)
    runs = _collection_runs(import_source)
    content["items"] = imported["items"] + content["items"]
    content["platforms"] = _merge_platform_counts(imported["platforms"], content["platforms"])
    content["total"] = len(content["items"])
    content["generated_at"] = (
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    content["imports"] = {
        "total": len(imported["items"]),
        "platforms": imported["platforms"],
        "runs": runs,
        "audit": imported["audit"],
    }
    content["collection_runs"] = runs
    return _dedupe_public_content(content)


_ANALYSIS_DIMENSION_LABELS = {
    "case_type": "案例类型",
    "built_thing": "产物方向",
    "tool_stack": "工具栈",
    "target_audience": "目标受众",
    "hook": "叙事钩子",
    "content_value": "内容价值",
    "risk_flag": "风险标签",
}

_ANALYSIS_CORE_FIELDS = (
    "case_type",
    "built_thing",
    "tool_stack",
    "target_audience",
    "hook",
    "content_value",
)


def _analysis_labels(item: dict, key: str) -> list[str]:
    return list(dict.fromkeys(_topic_labels(item, key)))


def _analysis_rate(count: int, denominator: int) -> float:
    if not denominator:
        return 0.0
    return round(count / denominator, 4)


def _analysis_percent(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def _analysis_platform(item: dict) -> tuple[str, str]:
    platform_id = (item.get("platform_id") or "unknown").lower()
    if platform_id.startswith("douyin"):
        return "douyin", "抖音"
    if platform_id.startswith("xiaohongshu"):
        return "xiaohongshu", "小红书"
    return platform_id, item.get("platform_name") or platform_id or "未知来源"


def _analysis_is_structured(item: dict) -> bool:
    return bool(_analysis_labels(item, "case_type"))


def _analysis_is_candidate(item: dict) -> bool:
    return bool(
        set(_analysis_labels(item, "content_value"))
        & {"有结果", "可复刻"}
    )


def _analysis_has_risk(item: dict) -> bool:
    return bool(_analysis_labels(item, "risk_flag"))


def _analysis_dimension(items: list[dict], key: str, denominator: int) -> dict:
    counts = {}
    platform_counts = {}
    labeled_items = 0

    for item in items:
        labels = _analysis_labels(item, key)
        if labels:
            labeled_items += 1
        platform_id, platform_name = _analysis_platform(item)
        for label in labels:
            counts[label] = counts.get(label, 0) + 1
            platform_counts.setdefault(label, {})
            platform_counts[label].setdefault(
                platform_id,
                {"id": platform_id, "name": platform_name, "count": 0},
            )
            platform_counts[label][platform_id]["count"] += 1

    rows = []
    for name, count in sorted(
        counts.items(), key=lambda item: (-item[1], item[0].lower())
    ):
        rows.append(
            {
                "name": name,
                "count": count,
                "denominator": denominator,
                "rate": _analysis_rate(count, denominator),
                "platforms": sorted(
                    platform_counts.get(name, {}).values(),
                    key=lambda item: (-item["count"], item["name"]),
                ),
            }
        )

    return {
        "id": key,
        "label": _ANALYSIS_DIMENSION_LABELS[key],
        "denominator": denominator,
        "labeled_items": labeled_items,
        "coverage": _analysis_rate(labeled_items, denominator),
        "items": rows,
    }


def _analysis_date_window(items: list[dict]) -> dict:
    dates = []
    for item in items:
        value = (item.get("published_at") or "").strip()[:10]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            continue
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            continue
        dates.append(parsed)

    if not dates:
        return {"count": 0, "start": None, "end": None}
    return {
        "count": len(dates),
        "start": min(dates).isoformat(),
        "end": max(dates).isoformat(),
    }


def _analysis_platform_profiles(items: list[dict]) -> list[dict]:
    grouped = {}
    for item in items:
        platform_id, platform_name = _analysis_platform(item)
        grouped.setdefault(
            platform_id,
            {"id": platform_id, "name": platform_name, "items": []},
        )
        grouped[platform_id]["items"].append(item)

    total = len(items)
    profiles = []
    for group in grouped.values():
        group_items = group.pop("items")
        structured = [item for item in group_items if _analysis_is_structured(item)]
        structured_count = len(structured)
        dimensions = {
            key: _analysis_dimension(structured, key, structured_count)
            for key in ("case_type", "built_thing", "hook", "target_audience")
        }
        profiles.append(
            {
                **group,
                "count": len(group_items),
                "share": _analysis_rate(len(group_items), total),
                "structured_count": structured_count,
                "structured_rate": _analysis_rate(structured_count, len(group_items)),
                "candidate_count": sum(
                    1 for item in structured if _analysis_is_candidate(item)
                ),
                "risk_count": sum(1 for item in structured if _analysis_has_risk(item)),
                "top_labels": {
                    key: dimension["items"][:3]
                    for key, dimension in dimensions.items()
                },
            }
        )

    return sorted(profiles, key=lambda item: (-item["count"], item["name"]))


def _analysis_platform_comparisons(items: list[dict]) -> list[dict]:
    platform_items = {}
    for item in items:
        platform_id, platform_name = _analysis_platform(item)
        platform_items.setdefault(
            platform_id,
            {"id": platform_id, "name": platform_name, "items": []},
        )
        platform_items[platform_id]["items"].append(item)

    if len(platform_items) < 2:
        return []

    rows = []
    for key in ("case_type", "hook", "built_thing"):
        labels = set()
        counts_by_platform = {}
        for platform_id, platform in platform_items.items():
            counts = {}
            labeled_items = 0
            for item in platform["items"]:
                item_labels = _analysis_labels(item, key)
                if item_labels:
                    labeled_items += 1
                for label in item_labels:
                    labels.add(label)
                    counts[label] = counts.get(label, 0) + 1
            counts_by_platform[platform_id] = {
                "counts": counts,
                "denominator": labeled_items,
                "base_denominator": len(platform["items"]),
            }

        if any(
            value["denominator"] == 0 for value in counts_by_platform.values()
        ):
            continue

        for label in labels:
            platforms = []
            total_count = 0
            for platform_id, platform in platform_items.items():
                denominator = counts_by_platform[platform_id]["denominator"]
                base_denominator = counts_by_platform[platform_id]["base_denominator"]
                count = counts_by_platform[platform_id]["counts"].get(label, 0)
                total_count += count
                platforms.append(
                    {
                        "id": platform_id,
                        "name": platform["name"],
                        "count": count,
                        "denominator": denominator,
                        "rate": _analysis_rate(count, denominator),
                        "base_denominator": base_denominator,
                        "coverage": _analysis_rate(denominator, base_denominator),
                    }
                )
            if total_count < 10:
                continue
            rates = [platform["rate"] for platform in platforms]
            rows.append(
                {
                    "dimension": key,
                    "dimension_label": _ANALYSIS_DIMENSION_LABELS[key],
                    "label": label,
                    "count": total_count,
                    "gap": round(max(rates) - min(rates), 4),
                    "platforms": sorted(platforms, key=lambda item: item["id"]),
                }
            )

    return sorted(
        rows,
        key=lambda item: (-item["gap"], -item["count"], item["label"]),
    )[:10]


def _analysis_opportunities(items: list[dict], denominator: int) -> list[dict]:
    grouped = {}
    for item in items:
        platform_id, platform_name = _analysis_platform(item)
        for label in _analysis_labels(item, "built_thing"):
            row = grouped.setdefault(
                label,
                {
                    "label": label,
                    "count": 0,
                    "candidate_count": 0,
                    "safe_candidate_count": 0,
                    "risk_count": 0,
                    "platforms": {},
                },
            )
            row["count"] += 1
            candidate = _analysis_is_candidate(item)
            risk = _analysis_has_risk(item)
            row["candidate_count"] += int(candidate)
            row["safe_candidate_count"] += int(candidate and not risk)
            row["risk_count"] += int(risk)
            row["platforms"].setdefault(
                platform_id,
                {"id": platform_id, "name": platform_name, "count": 0},
            )
            row["platforms"][platform_id]["count"] += 1

    rows = []
    for row in grouped.values():
        if row["count"] < 10:
            continue
        platforms = sorted(
            row.pop("platforms").values(),
            key=lambda item: (-item["count"], item["name"]),
        )
        rows.append(
            {
                **row,
                "denominator": denominator,
                "share": _analysis_rate(row["count"], denominator),
                "candidate_rate": _analysis_rate(
                    row["candidate_count"], row["count"]
                ),
                "safe_candidate_rate": _analysis_rate(
                    row["safe_candidate_count"], row["count"]
                ),
                "risk_rate": _analysis_rate(row["risk_count"], row["count"]),
                "platforms": platforms,
            }
        )

    return sorted(
        rows,
        key=lambda item: (
            -item["safe_candidate_count"],
            -item["candidate_count"],
            -item["count"],
            item["label"],
        ),
    )[:8]


def _analysis_recipes(items: list[dict], denominator: int) -> list[dict]:
    grouped = {}
    for item in items:
        built_labels = _analysis_labels(item, "built_thing")
        hook_labels = _analysis_labels(item, "hook")
        for built_label in built_labels:
            for hook_label in hook_labels:
                key = (built_label, hook_label)
                row = grouped.setdefault(
                    key,
                    {
                        "built_thing": built_label,
                        "hook": hook_label,
                        "count": 0,
                        "candidate_count": 0,
                        "safe_candidate_count": 0,
                    },
                )
                row["count"] += 1
                candidate = _analysis_is_candidate(item)
                row["candidate_count"] += int(candidate)
                row["safe_candidate_count"] += int(
                    candidate and not _analysis_has_risk(item)
                )

    rows = []
    for row in grouped.values():
        if row["count"] < 10:
            continue
        rows.append(
            {
                **row,
                "denominator": denominator,
                "share": _analysis_rate(row["count"], denominator),
                "candidate_rate": _analysis_rate(
                    row["candidate_count"], row["count"]
                ),
            }
        )
    return sorted(
        rows,
        key=lambda item: (
            -item["safe_candidate_count"],
            -item["candidate_count"],
            -item["count"],
        ),
    )[:6]


def _analysis_field_quality(items: list[dict], structured: list[dict]) -> dict:
    core_fields = []
    for key in _ANALYSIS_CORE_FIELDS:
        count = sum(1 for item in structured if _analysis_labels(item, key))
        core_fields.append(
            {
                "id": key,
                "label": _ANALYSIS_DIMENSION_LABELS[key],
                "count": count,
                "denominator": len(structured),
                "rate": _analysis_rate(count, len(structured)),
                "missing": max(len(structured) - count, 0),
            }
        )

    auxiliary_labels = {
        "published_at": "发布时间",
        "hot_score": "热度分",
        "likes": "点赞",
        "comments": "评论",
        "collects": "收藏",
        "shares": "分享",
        "cover_url": "封面",
    }
    auxiliary_fields = []
    for key, label in auxiliary_labels.items():
        count = sum(1 for item in items if str(item.get(key) or "").strip())
        auxiliary_fields.append(
            {
                "id": key,
                "label": label,
                "count": count,
                "denominator": len(items),
                "rate": _analysis_rate(count, len(items)),
                "missing": max(len(items) - count, 0),
            }
        )

    completed_cells = sum(field["count"] for field in core_fields)
    possible_cells = len(structured) * len(core_fields)
    return {
        "core_completeness": _analysis_rate(completed_cells, possible_cells),
        "core_fields": core_fields,
        "auxiliary_fields": auxiliary_fields,
    }


def _build_analysis_report(content: dict, generated_at: str) -> dict:
    items = list(content.get("items", []))
    structured = [item for item in items if _analysis_is_structured(item)]
    total = len(items)
    structured_count = len(structured)
    unstructured_count = total - structured_count
    candidates = [item for item in structured if _analysis_is_candidate(item)]
    risk_items = [item for item in structured if _analysis_has_risk(item)]
    safe_candidates = [item for item in candidates if not _analysis_has_risk(item)]
    risky_candidates = [item for item in candidates if _analysis_has_risk(item)]

    dimensions = [
        _analysis_dimension(structured, key, structured_count)
        for key in _ANALYSIS_DIMENSION_LABELS
    ]
    dimensions_by_id = {dimension["id"]: dimension for dimension in dimensions}
    platforms = _analysis_platform_profiles(items)
    comparisons = _analysis_platform_comparisons(structured)
    opportunities = _analysis_opportunities(structured, structured_count)
    recipes = _analysis_recipes(structured, structured_count)
    quality = _analysis_field_quality(items, structured)
    import_audit = dict(content.get("imports", {}).get("audit", {}))
    deduplication = dict(content.get("deduplication", {}))
    unit = (
        "精确 URL 唯一内容"
        if not int(deduplication.get("missing_url_items", 0) or 0)
        else "内容条目；有 URL 时按精确 URL 去重"
    )
    raw_rows = int(import_audit.get("raw_rows", 0) or 0)
    duplicate_urls = int(import_audit.get("duplicate_urls", 0) or 0)
    all_window = _analysis_date_window(items)
    structured_window = _analysis_date_window(structured)
    unstructured_window = _analysis_date_window(
        [item for item in items if not _analysis_is_structured(item)]
    )

    freshness_days = None
    if structured_window["end"]:
        generated_date = datetime.fromisoformat(
            generated_at.replace("Z", "+00:00")
        ).date()
        freshness_days = max(
            (generated_date - datetime.strptime(
                structured_window["end"], "%Y-%m-%d"
            ).date()).days,
            0,
        )

    case_rows = dimensions_by_id["case_type"]["items"]
    built_rows = dimensions_by_id["built_thing"]["items"]
    top_case = case_rows[0] if case_rows else None
    top_built = built_rows[0] if built_rows else None
    if top_case and top_built:
        headline = f"样本以「{top_case['name']}」为主，「{top_built['name']}」最集中"
    else:
        headline = "当前样本尚不足以形成结构化判断"
    summary = (
        f"本报告分析 {total} 条{unit}，其中 {structured_count} 条含结构化选题标签。"
        f"{len(safe_candidates)} 条同时具备“有结果/可复刻”信号且未标风险，可进入优先人工复核；"
        "所有结论只描述当前样本构成，不代表全网趋势、平台偏好或因果表现。"
    )

    insights = []
    comparison_lookup = {
        (row["dimension"], row["label"]): row for row in comparisons
    }
    true_case = comparison_lookup.get(("case_type", "真案例"))
    tutorial = comparison_lookup.get(("case_type", "教程"))
    if true_case and tutorial:
        true_rates = {item["id"]: item for item in true_case["platforms"]}
        tutorial_rates = {item["id"]: item for item in tutorial["platforms"]}
        xhs_true = true_rates.get("xiaohongshu")
        douyin_tutorial = tutorial_rates.get("douyin")
        if xhs_true and douyin_tutorial:
            insights.append(
                {
                    "priority": "P1",
                    "type": "平台实验",
                    "title": "用同题双版本验证平台化表达",
                    "evidence": (
                        f"小红书结构化样本中“真案例”占 {_analysis_percent(xhs_true['rate'])} "
                        f"（{xhs_true['count']}/{xhs_true['denominator']}）；"
                        f"抖音中“教程”占 {_analysis_percent(douyin_tutorial['rate'])} "
                        f"（{douyin_tutorial['count']}/{douyin_tutorial['denominator']}）。"
                    ),
                    "judgment": "差异可用于提出内容实验假设，但采集词与来源并未受控，不能解释为平台用户偏好。",
                    "action": "选 10 个相同主题，各制作“结果证据版”和“过程教学版”，在同一窗口按平台分别发布并记录平台内指标。",
                    "owner": "内容策略",
                    "acceptance": "同题、同窗口、每种脚本至少 10 条；只做平台内比较。",
                }
            )

    if opportunities:
        top = opportunities[0]
        insights.append(
            {
                "priority": "P1",
                "type": "候选池",
                "title": f"先复核「{top['label']}」低风险候选",
                "evidence": (
                    f"该方向共 {top['count']} 条，其中 {top['safe_candidate_count']} 条"
                    f"具备“有结果/可复刻”信号且未标风险。"
                ),
                "judgment": "这是当前样本里可直接进入编辑复核的最大队列，代表供给密度，不代表传播表现。",
                "action": "优先抽取 12 条，逐条核对原文证据、可复刻步骤与失败边界，再拆为结果、过程、反例三类选题。",
                "owner": "选题编辑",
                "acceptance": "每条保留原文链接、证据摘要、风险结论和建议平台。",
            }
        )

    risk_dimension = dimensions_by_id["risk_flag"]
    top_risk = risk_dimension["items"][0] if risk_dimension["items"] else None
    if top_risk:
        insights.append(
            {
                "priority": "P0",
                "type": "风险治理",
                "title": "把风险标签变成发布前质检门",
                "evidence": (
                    f"{len(risk_items)}/{structured_count} 条结构化样本至少带一个风险标签"
                    f"（{_analysis_percent(_analysis_rate(len(risk_items), structured_count))}）；"
                    f"首要风险是“{top_risk['name']}”{top_risk['count']} 条。"
                ),
                "judgment": "风险标签可能重叠，适合建立人工复核队列，不应直接删除或判定内容失真。",
                "action": "发布前逐条检查来源、商业关系、信息密度和活动语境；风险未解除的内容只留在观察池。",
                "owner": "内容审核",
                "acceptance": "风险队列 100% 留下复核结论与处理人。",
            }
        )

    lowest_field = min(
        quality["core_fields"], key=lambda item: (item["rate"], item["label"])
    ) if quality["core_fields"] else None
    if lowest_field and structured_count:
        insights.append(
            {
                "priority": "P2",
                "type": "数据质量",
                "title": f"先补齐“{lowest_field['label']}”再做细分比较",
                "evidence": (
                    f"该字段仅覆盖 {lowest_field['count']}/{lowest_field['denominator']} 条"
                    f"（{_analysis_percent(lowest_field['rate'])}），缺失 {lowest_field['missing']} 条。"
                ),
                "judgment": "缺失值会放大已标注类别的占比，当前只能描述已标样本，不能把空值视为否定。",
                "action": "下一批采集把该字段设为必填，并对高优先级候选做回填；覆盖率达到 90% 后再做类别排名。",
                "owner": "数据维护",
                "acceptance": "新批次该字段覆盖率不低于 90%，并记录空值原因。",
            }
        )

    return {
        "version": 1,
        "scope": {
            "unit": unit,
            "generated_at": generated_at,
            "total_items": total,
            "structured_items": structured_count,
            "unstructured_items": unstructured_count,
            "structured_rate": _analysis_rate(structured_count, total),
            "source_files": len(content.get("collection_runs", [])),
            "date_windows": {
                "all": all_window,
                "structured": structured_window,
                "unstructured": unstructured_window,
            },
            "freshness_days": freshness_days,
        },
        "executive_summary": {
            "headline": headline,
            "summary": summary,
        },
        "sample_quality": {
            "raw_rows": raw_rows,
            "unique_items": total,
            "duplicate_urls": duplicate_urls,
            "duplicate_rate": _analysis_rate(duplicate_urls, raw_rows),
            "merged_duplicate_urls": int(
                deduplication.get("merged_duplicate_urls", 0) or 0
            ),
            "url_items": int(deduplication.get("url_items", 0) or 0),
            "missing_url_items": int(
                deduplication.get("missing_url_items", 0) or 0
            ),
            "import_audit": import_audit,
            "field_quality": quality,
        },
        "candidate_pool": {
            "count": len(candidates),
            "denominator": structured_count,
            "rate": _analysis_rate(len(candidates), structured_count),
            "safe_count": len(safe_candidates),
            "safe_rate": _analysis_rate(len(safe_candidates), structured_count),
            "risk_count": len(risky_candidates),
            "risk_rate": _analysis_rate(len(risky_candidates), structured_count),
        },
        "risk_summary": {
            "count": len(risk_items),
            "denominator": structured_count,
            "rate": _analysis_rate(len(risk_items), structured_count),
            "items": risk_dimension["items"],
        },
        "platforms": platforms,
        "dimensions": dimensions,
        "platform_comparisons": comparisons,
        "opportunities": opportunities,
        "recipes": recipes,
        "insights": insights,
        "methodology": {
            "rules": [
                "CSV 导入内与跨来源合并后都会按精确 URL 去重；导入重复率来自 CSV 逐行审计。",
                "结构化标签分析以含案例类型的样本为分母；空值不按否定值处理。",
                "风险标签可重叠，因此各风险项占比之和可能超过风险样本占比。",
                "平台差异只描述当前采集样本，并未控制关键词、窗口和来源。",
                "页面生成时间不等于数据采集时间；报告同时展示数据截止日。",
            ],
            "safe_claims": [
                "当前样本的来源构成、标签覆盖、字段完整度与精确 URL 重复率",
                "带明确分母的平台样本差异与风险复核队列",
                "基于“有结果/可复刻”且无风险标签的人工候选池",
            ],
            "unsupported_claims": [
                "全网趋势、市场份额、增长率或平台用户偏好",
                "真实抓取成功率、失败率、纳入率或采集健康度",
                "爆款概率、转化率、因果效果或跨平台原始热度比较",
            ],
        },
    }


def _build_content_keyword_stats(content: dict) -> list:
    keywords = {}
    platform_counts = {}

    for item in content.get("items", []):
        platform_name = item.get("platform_name") or item.get("platform_id") or "未知平台"
        for key in _ANALYSIS_DIMENSION_LABELS:
            for label in _analysis_labels(item, key):
                identity = (key, label)
                keywords[identity] = keywords.get(identity, 0) + 1
                platform_counts.setdefault(identity, {})
                platform_counts[identity][platform_name] = (
                    platform_counts[identity].get(platform_name, 0) + 1
                )

    return [
        {
            "name": name,
            "dimension": key,
            "dimension_label": _ANALYSIS_DIMENSION_LABELS[key],
            "matched": count,
            "platforms": [
                {"name": platform_name, "matched": platform_count}
                for platform_name, platform_count in sorted(
                    platform_counts.get((key, name), {}).items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
        }
        for (key, name), count in sorted(
            keywords.items(),
            key=lambda item: (-item[1], item[0][1].lower(), item[0][0]),
        )
    ]


def _build_public_stats(content: dict, reports: list | None = None) -> dict:
    reports = reports or []
    content_total = int(content.get("total", 0) or 0)
    items = list(content.get("items", []))
    items_by_platform = {}
    for item in items:
        platform_id = item.get("platform_id") or item.get("platform_name") or "unknown"
        items_by_platform.setdefault(platform_id, []).append(item)

    platforms = []
    for platform in content.get("platforms", []):
        count = int(platform.get("count", 0) or 0)
        platform_id = platform.get("id") or platform.get("name") or "unknown"
        platform_items = items_by_platform.get(platform_id, [])
        platforms.append(
            {
                "id": platform_id,
                "name": platform.get("name") or platform.get("id") or "未知平台",
                "count": count,
                "crawled": count,
                "matched": count,
                "share": _analysis_rate(count, content_total),
                "structured_count": sum(
                    1 for item in platform_items if _analysis_is_structured(item)
                ),
            }
        )

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    analysis_report = _build_analysis_report(content, generated_at)
    return {
        "generated_at": generated_at,
        "latest_report": None,
        "totals": {
            "reports": len(reports),
            "content_items": content_total,
            "crawled_titles": content_total,
            "matched_titles": content_total,
            "failed_platforms": 0,
        },
        "platforms": platforms,
        "keywords": _build_content_keyword_stats(content),
        "failed_platforms": [],
        "collection_status": {
            "state": "not_connected",
            "label": "采集运行状态未接入",
            "detail": "当前静态产物未保存成功、失败与过滤日志，不能判断采集健康度。",
        },
        "analysis_report": analysis_report,
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

    reports = []
    content = _build_public_content(source, import_source)
    stats = _build_public_stats(content, reports)
    (dest / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
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
    print(f"Prepared content-only Pages artifact in {args.dest}")


if __name__ == "__main__":
    main()
