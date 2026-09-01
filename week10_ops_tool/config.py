"""Load and validate the feeds SLA configuration.

The config is a small YAML file that declares, for each expected data feed,
where its files land and how fresh they must be. Everything here is pure
parsing/validation so it can be unit tested without touching the filesystem
beyond reading the config file itself.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_DURATION_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([smhd])\s*$", re.IGNORECASE)
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


class ConfigError(ValueError):
    """Raised when the feeds config file is missing or malformed."""


def parse_duration(value) -> int:
    """Convert a duration like ``"26h"``, ``"90m"`` or ``"2d"`` into seconds.

    A bare number is treated as seconds. Raises :class:`ConfigError` on anything
    that is not a positive duration.
    """
    if isinstance(value, bool):  # bool is an int subclass; reject it explicitly
        raise ConfigError(f"duration must be a string like '26h', got {value!r}")
    if isinstance(value, (int, float)):
        if value <= 0:
            raise ConfigError(f"duration must be positive, got {value!r}")
        return int(value)
    if not isinstance(value, str):
        raise ConfigError(f"duration must be a string like '26h', got {value!r}")
    match = _DURATION_RE.match(value)
    if not match:
        raise ConfigError(
            f"invalid duration {value!r}; use <number><unit> with unit s, m, h or d"
        )
    amount, unit = match.groups()
    seconds = int(float(amount) * _UNIT_SECONDS[unit.lower()])
    if seconds <= 0:
        raise ConfigError(f"duration must be positive, got {value!r}")
    return seconds


def _humanize_seconds(seconds: int) -> str:
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if seconds >= size and seconds % size == 0:
            return f"{seconds // size}{unit}"
    return f"{seconds}s"


@dataclass(frozen=True)
class FeedSpec:
    """One expected feed and its freshness SLA."""

    name: str
    pattern: str
    max_age_seconds: int
    min_bytes: int = 1
    required: bool = True

    @property
    def max_age_human(self) -> str:
        return _humanize_seconds(self.max_age_seconds)


@dataclass(frozen=True)
class Config:
    drop_folder: Path
    feeds: list[FeedSpec]


def load_config(config_path, drop_folder_override: str | None = None) -> Config:
    """Read and validate the YAML config at ``config_path``.

    ``drop_folder_override`` (from ``--drop-folder`` or ``DROP_FOLDER``) wins over
    the ``drop_folder`` key in the file when provided.
    """
    path = Path(config_path)
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"could not parse YAML in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"top level of {path} must be a mapping")

    drop_folder = drop_folder_override or raw.get("drop_folder")
    if not drop_folder:
        raise ConfigError(
            "drop_folder must be set in the config, or via DROP_FOLDER / --drop-folder"
        )

    feeds_raw = raw.get("feeds")
    if not isinstance(feeds_raw, list) or not feeds_raw:
        raise ConfigError(f"{path} must define a non-empty 'feeds' list")

    feeds: list[FeedSpec] = []
    seen: set[str] = set()
    for i, entry in enumerate(feeds_raw):
        if not isinstance(entry, dict):
            raise ConfigError(f"feeds[{i}] must be a mapping")

        name = entry.get("name")
        if not name or not isinstance(name, str):
            raise ConfigError(f"feeds[{i}] is missing a string 'name'")
        if name in seen:
            raise ConfigError(f"duplicate feed name: {name!r}")
        seen.add(name)

        pattern = entry.get("pattern")
        if not pattern or not isinstance(pattern, str):
            raise ConfigError(f"feed {name!r} is missing a string 'pattern'")

        if "max_age" not in entry:
            raise ConfigError(f"feed {name!r} is missing 'max_age'")
        max_age_seconds = parse_duration(entry["max_age"])

        min_bytes = entry.get("min_bytes", 1)
        if isinstance(min_bytes, bool) or not isinstance(min_bytes, int) or min_bytes < 0:
            raise ConfigError(f"feed {name!r} 'min_bytes' must be a non-negative integer")

        required = entry.get("required", True)
        if not isinstance(required, bool):
            raise ConfigError(f"feed {name!r} 'required' must be true or false")

        feeds.append(
            FeedSpec(
                name=name,
                pattern=pattern,
                max_age_seconds=max_age_seconds,
                min_bytes=min_bytes,
                required=required,
            )
        )

    return Config(drop_folder=Path(drop_folder), feeds=feeds)
