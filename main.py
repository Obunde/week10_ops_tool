#!/usr/bin/env python3
"""week10_ops_tool — Data Freshness / SLA Monitor (CLI entrypoint).

Scans a drop folder for expected data feeds and checks each against its
freshness SLA declared in a YAML config. Writes a timestamped report and, when
any feed is MISSING, LATE or EMPTY, emails an alert summary (or prints it, with
``--dry-run`` or when SMTP is not configured).

Exit codes:
    0  every feed within SLA
    1  at least one feed breached its SLA
    2  configuration error
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from ops_tool.checker import check_all, has_breach
from ops_tool.config import ConfigError, load_config
from ops_tool.notifier import NotifyError, deliver
from ops_tool.report import (
    breach_count,
    render_json,
    render_markdown,
    render_text,
    subject_line,
)

DEFAULT_CONFIG = "feeds.example.yaml"
DEFAULT_DROP_FOLDER = "./sample_data/inbox"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="week10_ops_tool",
        description="Monitor data feeds in a drop folder against freshness SLAs.",
    )
    parser.add_argument(
        "--config",
        default=os.getenv("FEEDS_CONFIG", DEFAULT_CONFIG),
        help=f"path to the feeds YAML config (env: FEEDS_CONFIG, default: {DEFAULT_CONFIG})",
    )
    parser.add_argument(
        "--drop-folder",
        default=os.getenv("DROP_FOLDER"),
        help="override the drop folder path (env: DROP_FOLDER)",
    )
    parser.add_argument(
        "--report-dir",
        default=os.getenv("REPORT_DIR", "./reports"),
        help="directory for timestamped reports (env: REPORT_DIR, default: ./reports)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="never send email; print the alert to stdout instead",
    )
    parser.add_argument(
        "--no-report-files",
        action="store_true",
        help="do not write report files, only print to stdout",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="only produce output when there is a breach (good for cron)",
    )
    parser.add_argument(
        "--seed-samples",
        action="store_true",
        help="create sample feed files with back-dated timestamps, then exit",
    )
    return parser


def seed_samples(drop_folder: Path) -> None:
    """Create a deterministic set of sample feeds for a first run / demo."""
    drop_folder.mkdir(parents=True, exist_ok=True)
    now = time.time()
    hour = 3600
    # (filename, contents, age_seconds, expected outcome)
    plan = [
        ("orders_2026-09-01.csv", "id,amount\n1,10.00\n2,20.00\n3,5.50\n", 2 * hour),
        ("inventory_2026-08-30.csv", "sku,qty\n" + "".join(f"SKU{i},7\n" for i in range(40)), 50 * hour),
        ("clickstream_2026-09-01.csv", "", 1 * hour),
        # payments_*.csv is intentionally not created -> MISSING
    ]
    for name, contents, age in plan:
        fp = drop_folder / name
        fp.write_text(contents)
        os.utime(fp, (now - age, now - age))

    print(f"Seeded {len(plan)} sample files in {drop_folder}/")
    print("  orders_2026-09-01.csv       -> expect OK (2h old)")
    print("  inventory_2026-08-30.csv    -> expect LATE (50h old, SLA 26h)")
    print("  clickstream_2026-09-01.csv  -> expect EMPTY (0 bytes)")
    print("  payments_*.csv              -> expect MISSING (no file created)")


def write_report_files(report_dir: Path, text: str, md: str, js: str) -> list[Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    txt_path = report_dir / f"freshness_{stamp}.txt"
    md_path = report_dir / f"freshness_{stamp}.md"
    json_path = report_dir / f"freshness_{stamp}.json"
    txt_path.write_text(text + "\n")
    md_path.write_text(md + "\n")
    json_path.write_text(js + "\n")
    return [txt_path, md_path, json_path]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_dotenv()

    if args.seed_samples:
        seed_samples(Path(args.drop_folder or DEFAULT_DROP_FOLDER))
        return 0

    try:
        config = load_config(args.config, drop_folder_override=args.drop_folder)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    verbose = not args.quiet

    if not config.drop_folder.is_dir():
        print(
            f"warning: drop folder {config.drop_folder} does not exist; "
            "required feeds will report MISSING",
            file=sys.stderr,
        )

    results = check_all(config)
    breach = has_breach(results)

    text = render_text(results)
    markdown = render_markdown(results)
    js = render_json(results)

    if verbose or breach:
        print(text)

    if not args.no_report_files:
        try:
            written = write_report_files(Path(args.report_dir), text, markdown, js)
            if verbose or breach:
                print("\nReports written:")
                for p in written:
                    print(f"  {p}")
        except OSError as exc:
            print(f"warning: could not write report files: {exc}", file=sys.stderr)

    if breach:
        subject = subject_line(results)
        try:
            deliver(subject, text, dry_run=args.dry_run)
        except NotifyError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"\nExit 1 — {breach_count(results)} feed(s) breached SLA.")
        return 1

    if verbose:
        print("\nAll feeds within SLA — no alert sent. Exit 0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
