"""Render check results as plain text, Markdown, or JSON."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from .checker import FeedResult, Status

# Worst first, so the top of every report is the thing that needs attention.
_STATUS_ORDER = {Status.MISSING: 0, Status.EMPTY: 1, Status.LATE: 2, Status.OK: 3}


def _sorted_results(results: list[FeedResult]) -> list[FeedResult]:
    return sorted(results, key=lambda r: (_STATUS_ORDER[r.status], r.name))


def summary_counts(results: list[FeedResult]) -> dict[str, int]:
    counts = {s.value: 0 for s in Status}
    for r in results:
        counts[r.status.value] += 1
    return counts


def breach_count(results: list[FeedResult]) -> int:
    return sum(1 for r in results if not r.ok)


def render_text(results: list[FeedResult], generated_at: datetime | None = None) -> str:
    generated_at = generated_at or datetime.now(timezone.utc)
    rows = _sorted_results(results)
    name_w = max([len("FEED")] + [len(r.name) for r in rows])

    header = f"{'FEED':<{name_w}}  {'STATUS':<8}  DETAIL"
    body_rows = [
        f"{r.name:<{name_w}}  {r.status.value:<8}  {r.detail}" for r in rows
    ]
    rule_w = max([60, len(header)] + [len(row) for row in body_rows])
    lines = [
        f"Data Freshness Report  -  {generated_at:%Y-%m-%d %H:%M:%S %Z}",
        "=" * rule_w,
        header,
        "-" * rule_w,
        *body_rows,
        "-" * rule_w,
    ]

    counts = summary_counts(results)
    lines.append("Totals: " + ", ".join(f"{k}={v}" for k, v in counts.items()))
    breaches = breach_count(results)
    lines.append(
        f"RESULT: {'BREACH' if breaches else 'ALL OK'} "
        f"({breaches} of {len(rows)} feed(s) need attention)"
    )
    return "\n".join(lines)


def render_markdown(results: list[FeedResult], generated_at: datetime | None = None) -> str:
    generated_at = generated_at or datetime.now(timezone.utc)
    rows = _sorted_results(results)
    lines = [
        f"**Data Freshness Report** — {generated_at:%Y-%m-%d %H:%M:%S %Z}",
        "",
        "| Feed | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for r in rows:
        lines.append(f"| {r.name} | {r.status.value} | {r.detail} |")
    counts = summary_counts(results)
    lines += ["", "Totals: " + ", ".join(f"`{k}={v}`" for k, v in counts.items())]
    return "\n".join(lines)


def render_json(results: list[FeedResult], generated_at: datetime | None = None) -> str:
    generated_at = generated_at or datetime.now(timezone.utc)
    payload = {
        "generated_at": generated_at.isoformat(),
        "totals": summary_counts(results),
        "breach": breach_count(results) > 0,
        "feeds": [
            {
                "name": r.name,
                "status": r.status.value,
                "detail": r.detail,
                "file": str(r.file_path) if r.file_path else None,
                "age_seconds": round(r.age_seconds, 1) if r.age_seconds is not None else None,
                "size_bytes": r.size_bytes,
                "pattern": r.spec.pattern,
                "max_age_seconds": r.spec.max_age_seconds,
                "min_bytes": r.spec.min_bytes,
                "required": r.spec.required,
            }
            for r in _sorted_results(results)
        ],
    }
    return json.dumps(payload, indent=2)


def subject_line(results: list[FeedResult]) -> str:
    breaches = breach_count(results)
    if breaches:
        return f"[week10_ops_tool] ALERT: {breaches} data feed(s) need attention"
    return "[week10_ops_tool] OK: all data feeds fresh"
