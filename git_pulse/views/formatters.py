"""Formatting helpers for CLI display."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Sequence


SPARK_CHARS = (" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█")


def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable representation."""
    if num_bytes < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def relative_time(timestamp: int | float | datetime) -> str:
    """Format a timestamp into a friendly relative time string."""
    now = time.time()
    if isinstance(timestamp, datetime):
        ts = timestamp.timestamp()
    else:
        ts = float(timestamp)

    diff = now - ts
    if diff < 0:
        return "in the future"
    if diff < 60:
        return f"{int(diff)}s ago"
    if diff < 3600:
        return f"{int(diff // 60)}m ago"
    if diff < 86400:
        return f"{int(diff // 3600)}h ago"
    if diff < 86400 * 30:
        days = int(diff // 86400)
        return f"{days}d ago"
    if diff < 86400 * 365:
        months = int(diff // (86400 * 30))
        return f"{months}mo ago"
    years = int(diff // (86400 * 365))
    return f"{years}y ago"


def generate_sparkline(values: Sequence[int]) -> str:
    """Convert a sequence of integers into a unicode sparkline string."""
    if not values:
        return ""
    max_val = max(values)
    min_val = min(values)

    if max_val == 0:
        return SPARK_CHARS[0] * len(values)

    res = []
    # If all values are the same and non-zero, pick a middle block
    if max_val == min_val:
        return SPARK_CHARS[4] * len(values)

    spread = max_val - min_val
    for v in values:
        idx = int(((v - min_val) / spread) * (len(SPARK_CHARS) - 1))
        idx = max(0, min(len(SPARK_CHARS) - 1, idx))
        res.append(SPARK_CHARS[idx])
    return "".join(res)


def make_bar(value: int, total: int, width: int = 15) -> str:
    """Generate a simple progress block bar."""
    if total <= 0:
        pct = 0.0
    else:
        pct = min(1.0, max(0.0, value / total))
    filled = int(round(pct * width))
    empty = width - filled
    return "█" * filled + "░" * empty


def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text safely with an ellipsis."""
    text = text.strip().replace("\n", " ")
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
