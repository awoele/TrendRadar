import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Iterable


API_URL = "https://api.tikhub.io/api/v1/douyin/search/fetch_video_search_v2"
SOURCE_NAME = "tikhub:douyin_keyword_search"
CSV_FIELDS = [
    "platform",
    "title",
    "url",
    "cover_url",
    "author",
    "published_at",
    "like_count",
    "comment_count",
    "collect_count",
    "share_count",
    "description",
    "source",
    "keyword",
]


def strip_env_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def load_local_env(root: Path) -> None:
    env_path = root / ".env.local"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = strip_env_quotes(value)


def load_keyword_rules(path: Path) -> tuple[list[str], list[str]]:
    keywords = []
    excludes = []
    in_global_filter = False

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line == "[GLOBAL_FILTER]":
            in_global_filter = True
            continue
        if line.startswith("@"):
            continue

        if in_global_filter:
            excludes.append(line[1:].strip() if line.startswith("!") else line)
            continue

        if line.startswith("!"):
            continue
        if line.startswith("+"):
            line = line[1:].strip()
        if line:
            keywords.append(line)

    return list(dict.fromkeys(keywords)), list(dict.fromkeys(excludes))


def split_keywords(value: str) -> list[str]:
    keywords = []
    for keyword in value.replace("\n", ",").split(","):
        keyword = keyword.strip()
        if keyword and keyword not in keywords:
            keywords.append(keyword)
    return keywords


def first_media_url(value) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        for item in value:
            url = first_media_url(item)
            if url:
                return url
    if isinstance(value, dict):
        for key in (
            "url",
            "url_list",
            "urls",
            "uri",
            "cover_url",
            "coverUrl",
            "cover",
            "origin_cover",
            "dynamic_cover",
            "play_addr",
        ):
            url = first_media_url(value.get(key))
            if url:
                return url
    return ""


def first_text(*values) -> str:
    for value in values:
        if value is None:
            continue
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def nested_text(value: dict, *keys: str) -> str:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    return first_text(current)


def nested_value(value: dict, *keys: str):
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def metric_value(stats: dict, *keys: str) -> str:
    for key in keys:
        if isinstance(stats, dict) and stats.get(key) not in (None, ""):
            return str(stats.get(key))
    return ""


def parse_epoch_date(value, fallback: str) -> str:
    if value in (None, ""):
        return fallback
    try:
        timestamp = int(value)
    except (TypeError, ValueError):
        text = str(value).strip()
        if len(text) >= 10 and text[:4].isdigit():
            return text[:10]
        return fallback
    if timestamp > 10_000_000_000:
        timestamp = timestamp // 1000
    try:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
    except (OSError, OverflowError, ValueError):
        return fallback


def in_date_window(date_text: str, since: str = "", until: str = "") -> bool:
    if not date_text or len(date_text) < 10:
        return True
    date_text = date_text[:10]
    if since and date_text < since:
        return False
    if until and date_text > until:
        return False
    return True


def contains_excluded_text(row: dict, exclude_keywords: Iterable[str]) -> bool:
    text = " ".join(
        str(row.get(key) or "")
        for key in ("title", "description", "author", "keyword")
    ).lower()
    return any(keyword.lower() in text for keyword in exclude_keywords if keyword)


def looks_like_aweme(value: dict) -> bool:
    return any(key in value for key in ("aweme_id", "desc", "statistics", "video", "share_info"))


def normalize_candidate(value: dict) -> dict | None:
    for key in ("aweme_info", "aweme", "aweme_detail", "video_info"):
        child = value.get(key)
        if isinstance(child, dict) and looks_like_aweme(child):
            return child
    if looks_like_aweme(value):
        return value
    return None


def iter_aweme_candidates(value) -> Iterable[dict]:
    if isinstance(value, list):
        for item in value:
            yield from iter_aweme_candidates(item)
        return
    if not isinstance(value, dict):
        return

    candidate = normalize_candidate(value)
    if candidate:
        yield candidate

    for key in ("data", "aweme_list", "aweme_infos", "items", "list", "result"):
        child = value.get(key)
        if isinstance(child, (dict, list)):
            yield from iter_aweme_candidates(child)


def build_douyin_url(item: dict) -> str:
    url = first_text(
        item.get("share_url"),
        nested_text(item, "share_info", "share_url"),
        nested_text(item, "share_info", "url"),
        nested_text(item, "video", "share_url"),
    )
    if url:
        return url

    aweme_id = first_text(item.get("aweme_id"), item.get("id"), item.get("item_id"))
    if aweme_id:
        return f"https://www.douyin.com/video/{aweme_id}"
    return ""


def parse_search_items(
    payload: dict,
    keyword: str,
    today: str = "",
    since: str = "",
    until: str = "",
    max_items: int = 0,
    exclude_keywords: Iterable[str] = (),
) -> list[dict]:
    fallback_date = today or datetime.now().strftime("%Y-%m-%d")
    rows = []
    seen = set()

    for item in iter_aweme_candidates(payload):
        title = first_text(item.get("desc"), item.get("title"), item.get("caption"))
        url = build_douyin_url(item)
        if not title or not url:
            continue

        published_at = parse_epoch_date(
            first_text(item.get("create_time"), item.get("createTime"), item.get("publish_time")),
            fallback_date,
        )
        if not in_date_window(published_at, since=since, until=until):
            continue

        dedupe_key = url or f"{keyword}:{title}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        stats = item.get("statistics") or item.get("stats") or {}
        video = item.get("video") or {}
        row = {
            "platform": "douyin",
            "title": title,
            "url": url,
            "cover_url": first_media_url(
                nested_value(video, "cover")
                or nested_value(video, "origin_cover")
                or nested_value(video, "dynamic_cover")
                or item.get("cover")
                or item.get("images")
            ),
            "author": first_text(
                nested_text(item, "author", "nickname"),
                nested_text(item, "author", "unique_id"),
                nested_text(item, "author_user_info", "nickname"),
            ),
            "published_at": published_at,
            "like_count": metric_value(stats, "digg_count", "like_count", "likes"),
            "comment_count": metric_value(stats, "comment_count", "comments"),
            "collect_count": metric_value(stats, "collect_count", "collects"),
            "share_count": metric_value(stats, "share_count", "shares"),
            "description": f"keyword={keyword}; {title}",
            "source": SOURCE_NAME,
            "keyword": keyword,
        }
        if contains_excluded_text(row, exclude_keywords):
            continue

        rows.append(row)
        if max_items and len(rows) >= max_items:
            break

    return rows


def build_request_body(
    keyword: str,
    cursor: int = 0,
    sort_type: str = "0",
    publish_time: str = "7",
    filter_duration: str = "0",
    content_type: str = "0",
    search_id: str = "",
    backtrace: str = "",
) -> dict:
    return {
        "keyword": keyword,
        "cursor": cursor,
        "sort_type": sort_type,
        "publish_time": publish_time,
        "filter_duration": filter_duration,
        "content_type": content_type,
        "search_id": search_id,
        "backtrace": backtrace,
    }


def fetch_search(
    api_key: str,
    keyword: str,
    api_url: str = API_URL,
    cursor: int = 0,
    sort_type: str = "0",
    publish_time: str = "7",
    filter_duration: str = "0",
    content_type: str = "0",
    search_id: str = "",
    backtrace: str = "",
) -> dict:
    body = build_request_body(
        keyword=keyword,
        cursor=cursor,
        sort_type=sort_type,
        publish_time=publish_time,
        filter_duration=filter_duration,
        content_type=content_type,
        search_id=search_id,
        backtrace=backtrace,
    )
    request = urllib.request.Request(
        api_url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "TrendRadar-TikHub-Douyin/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        return json.loads(response.read().decode("utf-8"))


def pagination_value(payload: dict, *names: str):
    stack = [payload]
    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            for name in names:
                if value.get(name) not in (None, ""):
                    return value.get(name)
            for key in ("data", "extra", "log_pb"):
                child = value.get(key)
                if isinstance(child, dict):
                    stack.append(child)
    return ""


def write_rows_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})


def default_output_path(root: Path, since: str, until: str) -> Path:
    start = since or datetime.now().strftime("%Y-%m-%d")
    end = until or datetime.now().strftime("%Y-%m-%d")
    return root / "data" / "imports" / f"03_douyin_tikhub_keyword_search_{start}_{end}.csv"


def resolve_keywords(args, root: Path) -> tuple[list[str], list[str]]:
    keyword_path = Path(args.keyword_file)
    if not keyword_path.is_absolute():
        keyword_path = root / keyword_path

    if args.keywords:
        keywords = split_keywords(args.keywords)
        excludes = load_keyword_rules(keyword_path)[1] if keyword_path.exists() else []
    else:
        keywords, excludes = load_keyword_rules(keyword_path)

    if args.keyword_limit > 0:
        keywords = keywords[: args.keyword_limit]
    return keywords, excludes


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    today = datetime.now().strftime("%Y-%m-%d")

    parser = argparse.ArgumentParser(description="Fetch TikHub Douyin keyword search into a standard import CSV.")
    parser.add_argument("--keywords", default="", help="Comma-separated keywords. Defaults to config/frequency_words.txt.")
    parser.add_argument("--keyword-file", default="config/frequency_words.txt")
    parser.add_argument("--keyword-limit", type=int, default=0)
    parser.add_argument("--max-per-keyword", type=int, default=30)
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--api-url", default=API_URL)
    parser.add_argument("--publish-time", default="7")
    parser.add_argument("--sort-type", default="0")
    parser.add_argument("--filter-duration", default="0")
    parser.add_argument("--content-type", default="0")
    parser.add_argument("--since", default="")
    parser.add_argument("--until", default="")
    parser.add_argument("--today", default=today)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    load_local_env(root)
    api_key = os.environ.get("TIKHUB_API_KEY", "").strip() or os.environ.get("TIKHUB_TOKEN", "").strip()
    if not api_key:
        raise SystemExit("TIKHUB_API_KEY is not configured. Put it in .env.local or the environment.")

    keywords, exclude_keywords = resolve_keywords(args, root)
    if not keywords:
        raise SystemExit("No Douyin search keywords found.")

    rows = []
    seen_urls = set()
    errors = []
    for keyword in keywords:
        cursor = 0
        search_id = ""
        backtrace = ""
        keyword_rows = []
        for _ in range(max(1, args.pages)):
            try:
                payload = fetch_search(
                    api_key=api_key,
                    keyword=keyword,
                    api_url=args.api_url,
                    cursor=cursor,
                    sort_type=args.sort_type,
                    publish_time=args.publish_time,
                    filter_duration=args.filter_duration,
                    content_type=args.content_type,
                    search_id=search_id,
                    backtrace=backtrace,
                )
            except urllib.error.HTTPError as exc:
                errors.append(f"{keyword}: HTTP {exc.code} {exc.reason}")
                break
            except urllib.error.URLError as exc:
                errors.append(f"{keyword}: {exc.reason}")
                break

            parsed_rows = parse_search_items(
                payload,
                keyword=keyword,
                today=args.today,
                since=args.since,
                until=args.until,
                max_items=max(0, args.max_per_keyword - len(keyword_rows)),
                exclude_keywords=exclude_keywords,
            )
            for row in parsed_rows:
                if row["url"] in seen_urls:
                    continue
                seen_urls.add(row["url"])
                keyword_rows.append(row)
            if args.max_per_keyword and len(keyword_rows) >= args.max_per_keyword:
                break

            next_cursor = pagination_value(payload, "cursor", "next_cursor", "nextCursor")
            cursor = int(next_cursor or 0)
            search_id = str(pagination_value(payload, "search_id", "searchId") or search_id)
            backtrace = str(pagination_value(payload, "backtrace") or backtrace)
            if not cursor and not search_id and not backtrace:
                break

        rows.extend(keyword_rows)

    out_path = args.out or default_output_path(root, args.since, args.until)
    if not out_path.is_absolute():
        out_path = root / out_path
    write_rows_csv(out_path, rows)

    print(
        json.dumps(
            {
                "source": SOURCE_NAME,
                "keywords": len(keywords),
                "rows": len(rows),
                "out": str(out_path),
                "errors": errors,
            },
            ensure_ascii=False,
        )
    )
    return 1 if errors and not rows else 0


if __name__ == "__main__":
    raise SystemExit(main())
