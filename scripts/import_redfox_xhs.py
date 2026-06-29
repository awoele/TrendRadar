from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


DEFAULT_KEYWORDS = [
    "vibecoding",
    "vibe coding",
    "Claude Code",
    "Codex",
    "Cursor",
    "AI Coding",
    "AI编程",
    "零代码开发",
    "AI建站",
    "独立开发",
    "Figma MCP",
    "VibeCoding大赏",
]


RAW_FIELDS = [
    "platform",
    "title",
    "url",
    "cover_url",
    "author",
    "published_at",
    "likes",
    "comments",
    "collects",
    "shares",
    "description",
    "source",
    "keyword",
    "work_id",
    "author_fans",
    "interactive_count",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import RedFox Xiaohongshu crawler results into TrendRadar topic imports."
    )
    parser.add_argument("--keyword", action="append", default=[], help="Keyword to crawl. Can be repeated.")
    parser.add_argument("--keywords", default="", help="Comma-separated keyword list.")
    parser.add_argument("--start-date", default="", help="Start date YYYY-MM-DD. Defaults to --days before end date.")
    parser.add_argument("--end-date", default="", help="End date YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--days", type=int, default=14, help="Days to look back when --start-date is omitted.")
    parser.add_argument("--sort-type", default="_4", choices=["_0", "_2", "_4"], help="RedFox sort type.")
    parser.add_argument("--skill-script", type=Path, default=None, help="Path to xiaohongshu-crawler crawl_xhs.py.")
    parser.add_argument("--classifier-root", type=Path, default=Path(r"D:\Documents\agents"), help="vibecase_agent repo root.")
    parser.add_argument("--raw-json-out", type=Path, default=None, help="Where to write combined raw JSON.")
    parser.add_argument("--raw-csv-out", type=Path, default=None, help="Where to write normalized raw CSV.")
    parser.add_argument("--classified-out-dir", type=Path, default=None, help="Where classifier outputs are written.")
    parser.add_argument("--import-out", type=Path, default=None, help="Final CSV copied into data/imports.")
    parser.add_argument("--keep-all-classified", action="store_true", help="Import cases_classified.csv instead of case_radar.csv.")
    return parser.parse_args(argv)


def parse_iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def resolve_dates(args: argparse.Namespace) -> tuple[str, str]:
    end = parse_iso_date(args.end_date) if args.end_date else date.today()
    start = parse_iso_date(args.start_date) if args.start_date else end - timedelta(days=args.days)
    if start > end:
        raise ValueError("--start-date cannot be after --end-date")
    return start.isoformat(), end.isoformat()


def split_keywords(args: argparse.Namespace) -> list[str]:
    keywords = []
    for value in args.keyword:
        keywords.extend(part.strip() for part in value.split(","))
    if args.keywords:
        keywords.extend(part.strip() for part in args.keywords.split(","))
    keywords = [keyword for keyword in keywords if keyword]
    return list(dict.fromkeys(keywords or DEFAULT_KEYWORDS))


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_skill_script() -> Path:
    workspace_root = repo_root().parent
    sibling = workspace_root / "skills" / "xiaohongshu-crawler" / "scripts" / "crawl_xhs.py"
    if sibling.exists():
        return sibling
    return Path.home() / ".qoderwork" / "skills" / "xiaohongshu-crawler" / "scripts" / "crawl_xhs.py"


def default_paths(start_date: str, end_date: str) -> dict[str, Path]:
    slug = f"redfox_xhs_vibecoding_{start_date}_{end_date}"
    return {
        "raw_json": repo_root() / ".tmp" / f"{slug}.json",
        "raw_csv": repo_root() / ".tmp" / f"{slug}_raw.csv",
        "classified": repo_root() / ".tmp" / f"{slug}_classified",
        "import_out": repo_root() / "data" / "imports" / f"01_{slug}.csv",
    }


def read_openclaw_key() -> str:
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        return ""
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    return str((data.get("env") or {}).get("REDFOX_API_KEY") or "")


def read_windows_env_key() -> str:
    if os.name != "nt":
        return ""
    try:
        import winreg
    except ImportError:
        return ""

    locations = [
        (winreg.HKEY_CURRENT_USER, "Environment"),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    ]
    for hive, subkey in locations:
        try:
            with winreg.OpenKey(hive, subkey) as key:
                value, _ = winreg.QueryValueEx(key, "REDFOX_API_KEY")
                if value:
                    return str(value)
        except OSError:
            continue
    return ""


def ensure_redfox_api_key() -> None:
    if os.environ.get("REDFOX_API_KEY"):
        return
    value = read_openclaw_key() or read_windows_env_key()
    if value:
        os.environ["REDFOX_API_KEY"] = value
        return
    raise RuntimeError("Missing REDFOX_API_KEY in process env, ~/.openclaw/openclaw.json, and Windows env.")


def load_crawler(script_path: Path):
    spec = importlib.util.spec_from_file_location("redfox_xhs_crawler", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load crawler script: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def crawl_keywords(script_path: Path, keywords: list[str], start_date: str, end_date: str, sort_type: str) -> dict:
    ensure_redfox_api_key()
    crawler = load_crawler(script_path)
    by_key: dict[str, dict] = {}
    combined = []
    for keyword in keywords:
        result = crawler.crawl(keyword, start_date=start_date, end_date=end_date, sort_type=sort_type)
        articles = result.get("articles") or []
        by_key[keyword] = {
            "total": len(articles),
            "relatedSearches": result.get("relatedSearches") or [],
            "hotTopics": result.get("hotTopics") or [],
        }
        for item in articles:
            combined.append({**item, "_keyword": keyword})
    deduped = dedupe_articles(combined)
    return {
        "meta": {
            "platform": "xiaohongshu",
            "keywords": keywords,
            "start_date": start_date,
            "end_date": end_date,
            "sort_type": sort_type,
            "total_before_dedupe": len(combined),
            "total_after_dedupe": len(deduped),
            "counts_by_keyword": by_key,
        },
        "articles": deduped,
    }


def dedupe_articles(items: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for item in items:
        key = item.get("work_id") or item.get("work_url") or item.get("title")
        if not key:
            key = json.dumps(item, ensure_ascii=False, sort_keys=True)
        old = seen.get(str(key))
        if old is None or to_int(item.get("interactive_count") or item.get("like_count")) > to_int(
            old.get("interactive_count") or old.get("like_count")
        ):
            seen[str(key)] = item
    return sorted(
        seen.values(),
        key=lambda item: (
            to_int(item.get("interactive_count")),
            to_int(item.get("like_count")),
            item.get("publish_time") or "",
        ),
        reverse=True,
    )


def to_int(value: object) -> int:
    try:
        return int(float(str(value or "0").replace(",", "")))
    except ValueError:
        return 0


def normalize_date(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    for fmt, size in (("%Y-%m-%d", 10), ("%Y-%m-%d %H:%M:%S", 19), ("%Y/%m/%d", 10), ("%Y%m%d", 8)):
        try:
            return datetime.strptime(text[:size], fmt).date().isoformat()
        except ValueError:
            continue
    return text[:10]


def article_to_row(item: dict) -> dict:
    keyword = str(item.get("_keyword") or "").strip()
    return {
        "platform": "xiaohongshu",
        "title": str(item.get("title") or "").strip(),
        "url": str(item.get("work_url") or "").strip(),
        "cover_url": normalize_cover_url(str(item.get("cover") or "")),
        "author": str(item.get("author") or "").strip(),
        "published_at": normalize_date(str(item.get("publish_time") or "")),
        "likes": str(item.get("like_count") or ""),
        "comments": str(item.get("comment_count") or ""),
        "collects": str(item.get("collect_count") or ""),
        "shares": str(item.get("share_count") or ""),
        "description": str(item.get("desc") or "").strip(),
        "source": f"redfox:xiaohongshu-crawler:{keyword}",
        "keyword": keyword,
        "work_id": str(item.get("work_id") or "").strip(),
        "author_fans": str(item.get("author_fans") or ""),
        "interactive_count": str(item.get("interactive_count") or ""),
    }


def normalize_cover_url(value: str) -> str:
    url = value.strip()
    if not url:
        return ""
    if url.startswith("//"):
        url = f"https:{url}"
    if url.startswith("http://"):
        url = "https://" + url[len("http://") :]
    return url


def write_raw_csv(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RAW_FIELDS)
        writer.writeheader()
        for item in payload["articles"]:
            row = article_to_row(item)
            if row["title"] and row["url"]:
                writer.writerow(row)


def run_classifier(raw_csv: Path, out_dir: Path, classifier_root: Path, start_date: str, end_date: str) -> Path:
    if not classifier_root.exists():
        raise FileNotFoundError(f"Missing classifier root: {classifier_root}")
    env = os.environ.copy()
    src = classifier_root / "src"
    env["PYTHONPATH"] = str(src) + os.pathsep + env.get("PYTHONPATH", "")
    out_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "vibecase_agent.cli",
        "--input",
        str(raw_csv),
        "--out",
        str(out_dir),
        "--no-web",
        "--since",
        start_date,
        "--until",
        end_date,
        "--today",
        end_date,
    ]
    subprocess.run(command, cwd=classifier_root, env=env, check=True)
    return out_dir / "case_radar.csv"


def write_enriched_import_csv(source: Path, dest: Path, raw_csv: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    raw_by_url = {}
    with raw_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("url"):
                raw_by_url[row["url"]] = row

    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = []
        for row in reader:
            raw = raw_by_url.get(row.get("url") or "") or {}
            for target, raw_key in (
                ("cover_url", "cover_url"),
                ("like_count", "likes"),
                ("comment_count", "comments"),
                ("collect_count", "collects"),
                ("share_count", "shares"),
            ):
                if not row.get(target) and raw.get(raw_key):
                    row[target] = raw[raw_key]
            if raw.get("source") and (not row.get("source") or row["source"].startswith("csv:")):
                row["source"] = raw["source"]
            rows.append(row)

    with dest.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def count_csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    start_date, end_date = resolve_dates(args)
    paths = default_paths(start_date, end_date)
    skill_script = args.skill_script or default_skill_script()
    raw_json = args.raw_json_out or paths["raw_json"]
    raw_csv = args.raw_csv_out or paths["raw_csv"]
    classified_out = args.classified_out_dir or paths["classified"]
    import_out = args.import_out or paths["import_out"]

    if not skill_script.exists():
        raise FileNotFoundError(f"Missing RedFox Xiaohongshu crawler script: {skill_script}")

    keywords = split_keywords(args)
    payload = crawl_keywords(skill_script, keywords, start_date, end_date, args.sort_type)

    raw_json.parent.mkdir(parents=True, exist_ok=True)
    raw_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_raw_csv(payload, raw_csv)

    classified_source = run_classifier(raw_csv, classified_out, args.classifier_root, start_date, end_date)
    if args.keep_all_classified:
        classified_source = classified_out / "cases_classified.csv"
    write_enriched_import_csv(classified_source, import_out, raw_csv)

    summary = {
        "keywords": len(keywords),
        "raw_before_dedupe": payload["meta"]["total_before_dedupe"],
        "raw_after_dedupe": payload["meta"]["total_after_dedupe"],
        "raw_csv_rows": count_csv_rows(raw_csv),
        "import_rows": count_csv_rows(import_out),
        "raw_json": str(raw_json),
        "raw_csv": str(raw_csv),
        "classified_out": str(classified_out),
        "import_out": str(import_out),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
