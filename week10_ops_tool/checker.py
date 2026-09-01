"""Core data-freshness checks.

For each configured feed we locate the newest matching file in the drop folder
and classify it:

* ``OK``      — a fresh, non-empty file exists (or an optional feed is absent)
* ``LATE``    — newest file is older than the feed's ``max_age`` SLA
* ``MISSING`` — a required feed has no matching file
* ``EMPTY``   — newest file is smaller than the feed's ``min_bytes``

``EMPTY`` is checked before ``LATE`` because a truncated file is the more urgent
signal.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .config import Config, FeedSpec


class Status(str, Enum):
    OK = "OK"
    LATE = "LATE"
    MISSING = "MISSING"
    EMPTY = "EMPTY"


@dataclass
class FeedResult:
    spec: FeedSpec
    status: Status
    detail: str
    file_path: Path | None = None
    age_seconds: float | None = None
    size_bytes: int | None = None

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def ok(self) -> bool:
        return self.status is Status.OK


def humanize_age(seconds: float) -> str:
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes and not days:
        parts.append(f"{minutes}m")
    return " ".join(parts) or "<1m"


def check_feed(spec: FeedSpec, drop_folder: Path, now: float | None = None) -> FeedResult:
    now = time.time() if now is None else now

    matches = [p for p in sorted(drop_folder.glob(spec.pattern)) if p.is_file()]
    if not matches:
        if spec.required:
            return FeedResult(
                spec=spec,
                status=Status.MISSING,
                detail=f"no file matching {spec.pattern!r} in {drop_folder}",
            )
        return FeedResult(
            spec=spec,
            status=Status.OK,
            detail=f"optional feed absent (pattern {spec.pattern!r})",
        )

    newest = max(matches, key=lambda p: p.stat().st_mtime)
    stat = newest.stat()
    age = now - stat.st_mtime
    size = stat.st_size

    if size < spec.min_bytes:
        return FeedResult(
            spec=spec,
            status=Status.EMPTY,
            detail=f"{newest.name} is {size} B (minimum {spec.min_bytes} B)",
            file_path=newest,
            age_seconds=age,
            size_bytes=size,
        )

    if age > spec.max_age_seconds:
        return FeedResult(
            spec=spec,
            status=Status.LATE,
            detail=(
                f"{newest.name} last modified {humanize_age(age)} ago "
                f"(SLA {spec.max_age_human})"
            ),
            file_path=newest,
            age_seconds=age,
            size_bytes=size,
        )

    return FeedResult(
        spec=spec,
        status=Status.OK,
        detail=f"{newest.name} fresh — {humanize_age(age)} old, {size} B",
        file_path=newest,
        age_seconds=age,
        size_bytes=size,
    )


def check_all(config: Config, now: float | None = None) -> list[FeedResult]:
    return [check_feed(spec, config.drop_folder, now=now) for spec in config.feeds]


def has_breach(results: list[FeedResult]) -> bool:
    return any(not r.ok for r in results)
