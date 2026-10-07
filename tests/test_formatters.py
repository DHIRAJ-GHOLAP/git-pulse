"""Tests for formatting utilities."""

from datetime import datetime, timezone
import time
from git_pulse.views.formatters import (
    format_bytes,
    generate_sparkline,
    make_bar,
    relative_time,
    truncate_text,
)


def test_format_bytes():
    assert format_bytes(0) == "0 B"
    assert format_bytes(512) == "512 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1024 * 1024 * 3) == "3.0 MB"
    assert format_bytes(1024 * 1024 * 1024 * 2) == "2.0 GB"


def test_relative_time():
    now = time.time()
    assert relative_time(now - 10) == "10s ago"
    assert relative_time(now - 120) == "2m ago"
    assert relative_time(now - 7200) == "2h ago"
    assert relative_time(now - 86400 * 4) == "4d ago"


def test_generate_sparkline():
    assert generate_sparkline([]) == ""
    assert generate_sparkline([0, 0, 0]) == "   "
    spark = generate_sparkline([1, 2, 5, 10])
    assert len(spark) == 4
    assert spark[-1] == "█"


def test_make_bar():
    assert make_bar(0, 10, width=10) == "░░░░░░░░░░"
    assert make_bar(10, 10, width=10) == "██████████"
    assert make_bar(5, 10, width=10) == "█████░░░░░"


def test_truncate_text():
    assert truncate_text("hello", 10) == "hello"
    assert truncate_text("this is a very long string that should be truncated", 15) == "this is a ve..."
