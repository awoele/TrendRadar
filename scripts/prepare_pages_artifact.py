import argparse
import json
import shutil
from datetime import datetime, timedelta
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


def prepare_pages_artifact(
    source: Path,
    dest: Path,
    keep_days: int = 7,
    panel_source: Path = Path("web/config-panel"),
) -> dict:
    source = Path(source)
    dest = Path(dest)
    panel_source = Path(panel_source)

    if not (source / "index.html").exists():
        raise FileNotFoundError(f"Missing public report: {source / 'index.html'}")

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    _copy_file(source / "index.html", dest / "index.html")
    (dest / ".nojekyll").write_text("", encoding="utf-8")
    config_panel = None

    if panel_source.exists():
        panel_dest = dest / "config"
        shutil.copytree(panel_source, panel_dest, dirs_exist_ok=True)
        if (panel_dest / "index.html").exists():
            config_panel = "config/index.html"

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

    manifest = {
        "latest": "index.html",
        "reports": reports,
        "keep_days": keep_days,
    }
    if config_panel:
        manifest["config_panel"] = config_panel
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
