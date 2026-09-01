"""Unit tests for the freshness classifier and duration parsing.

Run from the project root:  pytest
"""
from __future__ import annotations

import os
import time

import pytest

from ops_tool.checker import Status, check_all, check_feed, has_breach
from ops_tool.config import Config, ConfigError, FeedSpec, parse_duration


def _spec(name="feed", pattern="feed_*.csv", max_age="24h", min_bytes=5, required=True):
    return FeedSpec(
        name=name,
        pattern=pattern,
        max_age_seconds=parse_duration(max_age),
        min_bytes=min_bytes,
        required=required,
    )


def _make_file(folder, name, contents="col\n1\n2\n", age_seconds=0):
    fp = folder / name
    fp.write_text(contents)
    stamp = time.time() - age_seconds
    os.utime(fp, (stamp, stamp))
    return fp


@pytest.mark.parametrize("age,expected", [(3600, Status.OK), (100_000, Status.LATE)])
def test_age_classification(tmp_path, age, expected):
    _make_file(tmp_path, "feed_1.csv", age_seconds=age)
    assert check_feed(_spec(), tmp_path).status is expected


def test_missing_required(tmp_path):
    assert check_feed(_spec(), tmp_path).status is Status.MISSING


def test_missing_optional_is_ok(tmp_path):
    assert check_feed(_spec(required=False), tmp_path).status is Status.OK


def test_empty_file(tmp_path):
    _make_file(tmp_path, "feed_1.csv", contents="", age_seconds=0)
    assert check_feed(_spec(min_bytes=10), tmp_path).status is Status.EMPTY


def test_empty_takes_priority_over_late(tmp_path):
    _make_file(tmp_path, "feed_1.csv", contents="", age_seconds=100_000)
    assert check_feed(_spec(min_bytes=10), tmp_path).status is Status.EMPTY


def test_newest_file_wins(tmp_path):
    _make_file(tmp_path, "feed_old.csv", age_seconds=100_000)
    _make_file(tmp_path, "feed_new.csv", age_seconds=60)
    result = check_feed(_spec(), tmp_path)
    assert result.status is Status.OK
    assert result.file_path.name == "feed_new.csv"


def test_check_all_and_has_breach(tmp_path):
    _make_file(tmp_path, "feed_1.csv", age_seconds=60)
    config = Config(
        drop_folder=tmp_path,
        feeds=[_spec(), _spec(name="other", pattern="other_*.csv")],
    )
    results = check_all(config)
    assert len(results) == 2
    assert has_breach(results) is True  # 'other' is MISSING


def test_no_breach_when_all_ok(tmp_path):
    _make_file(tmp_path, "feed_1.csv", age_seconds=60)
    config = Config(drop_folder=tmp_path, feeds=[_spec()])
    assert has_breach(check_all(config)) is False


@pytest.mark.parametrize(
    "text,seconds",
    [("30s", 30), ("15m", 900), ("2h", 7200), ("1d", 86_400), ("1.5h", 5400)],
)
def test_parse_duration(text, seconds):
    assert parse_duration(text) == seconds


@pytest.mark.parametrize("bad", ["soon", "", "10", "5x", "-3h", 0, -5, True])
def test_parse_duration_rejects_bad_values(bad):
    with pytest.raises(ConfigError):
        parse_duration(bad)
