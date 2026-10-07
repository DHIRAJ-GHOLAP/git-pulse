"""Terminal contribution heatmap and hourly punchcard analyzer."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from git_pulse import git_utils


@dataclass
class HeatmapData:
    days: int
    start_date: date
    end_date: date
    total_commits: int
    daily_counts: dict[date, int]
    weeks_data: list[list[tuple[date, int, int]]]  # list of weeks, each week is list of 7 (date, count, level 0-4)
    current_streak: int
    longest_streak: int
    active_days: int
    busiest_day: Optional[tuple[date, int]]


@dataclass
class PunchcardData:
    grid: list[list[int]]  # 7 rows (Mon=0..Sun=6), 24 columns (hours 0..23)
    total_commits: int
    peak_hour: int
    peak_day_index: int
    peak_count: int


def analyze_heatmap(
    cwd: Optional[Path | str] = None,
    num_days: int = 180,
    author: Optional[str] = None,
) -> HeatmapData:
    """Analyze commit frequencies to construct a GitHub-like contribution grid."""
    root = git_utils.get_repo_root(cwd)
    if not root:
        raise git_utils.GitError("Not a git repository.")

    if not git_utils.has_commits(root):
        today = date.today()
        return HeatmapData(
            days=num_days,
            start_date=today - timedelta(days=num_days),
            end_date=today,
            total_commits=0,
            daily_counts={},
            weeks_data=[],
            current_streak=0,
            longest_streak=0,
            active_days=0,
            busiest_day=None,
        )

    since_date = date.today() - timedelta(days=num_days)
    since_ts = int(datetime(since_date.year, since_date.month, since_date.day).timestamp())

    cmd = ["log", f"--since={since_ts}", "--format=%ct"]
    if author:
        cmd.append(f"--author={author}")

    res = git_utils.run_git(cmd, cwd=root)
    daily_counts: dict[date, int] = defaultdict(int)
    total_commits = 0

    if res.returncode == 0 and res.stdout.strip():
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ts = int(line)
                d = datetime.fromtimestamp(ts).date()
                if d >= since_date:
                    daily_counts[d] += 1
                    total_commits += 1
            except ValueError:
                continue

    # Determine scale thresholds (levels 0 to 4)
    counts = [c for c in daily_counts.values() if c > 0]
    if counts:
        max_c = max(counts)
        th1 = max(1, int(max_c * 0.25))
        th2 = max(2, int(max_c * 0.50))
        th3 = max(3, int(max_c * 0.75))
    else:
        th1, th2, th3 = 1, 2, 3

    def get_level(c: int) -> int:
        if c == 0:
            return 0
        if c <= th1:
            return 1
        if c <= th2:
            return 2
        if c <= th3:
            return 3
        return 4

    # Build weekly columns aligned to Monday (weekday() == 0)
    end_date = date.today()
    # Align start date to the Monday of its week
    start_monday = since_date - timedelta(days=since_date.weekday())
    end_sunday = end_date + timedelta(days=(6 - end_date.weekday()))

    weeks_data: list[list[tuple[date, int, int]]] = []
    curr = start_monday
    current_week: list[tuple[date, int, int]] = []

    while curr <= end_sunday:
        cnt = daily_counts.get(curr, 0)
        lvl = get_level(cnt)
        current_week.append((curr, cnt, lvl))

        if len(current_week) == 7:
            weeks_data.append(current_week)
            current_week = []

        curr += timedelta(days=1)

    if current_week:
        weeks_data.append(current_week)

    # Compute streaks & stats
    busiest_day: Optional[tuple[date, int]] = None
    max_day_count = 0
    active_days = 0

    all_dates_in_range = []
    curr = since_date
    while curr <= end_date:
        all_dates_in_range.append(curr)
        c = daily_counts.get(curr, 0)
        if c > 0:
            active_days += 1
            if c > max_day_count:
                max_day_count = c
                busiest_day = (curr, c)
        curr += timedelta(days=1)

    # Longest and current streak
    longest_streak = 0
    curr_streak_run = 0
    for d in all_dates_in_range:
        if daily_counts.get(d, 0) > 0:
            curr_streak_run += 1
            if curr_streak_run > longest_streak:
                longest_streak = curr_streak_run
        else:
            curr_streak_run = 0

    # Current streak (looking backwards from today/yesterday)
    current_streak = 0
    d_check = end_date
    # Allow current streak to count if today has 0 commits but yesterday had commits
    if daily_counts.get(d_check, 0) == 0:
        d_check = end_date - timedelta(days=1)

    while d_check >= since_date and daily_counts.get(d_check, 0) > 0:
        current_streak += 1
        d_check -= timedelta(days=1)

    return HeatmapData(
        days=num_days,
        start_date=since_date,
        end_date=end_date,
        total_commits=total_commits,
        daily_counts=daily_counts,
        weeks_data=weeks_data,
        current_streak=current_streak,
        longest_streak=longest_streak,
        active_days=active_days,
        busiest_day=busiest_day,
    )


def analyze_punchcard(
    cwd: Optional[Path | str] = None,
    author: Optional[str] = None,
) -> PunchcardData:
    """Analyze commit timestamps by day-of-week (Mon-Sun) and hour (0-23)."""
    root = git_utils.get_repo_root(cwd)
    if not root:
        raise git_utils.GitError("Not a git repository.")

    grid = [[0 for _ in range(24)] for _ in range(7)]
    if not git_utils.has_commits(root):
        return PunchcardData(
            grid=grid,
            total_commits=0,
            peak_hour=0,
            peak_day_index=0,
            peak_count=0,
        )

    cmd = ["log", "--format=%ct"]
    if author:
        cmd.append(f"--author={author}")

    res = git_utils.run_git(cmd, cwd=root)
    total_commits = 0
    if res.returncode == 0 and res.stdout.strip():
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ts = int(line)
                dt = datetime.fromtimestamp(ts)
                dow = dt.weekday()  # 0 is Monday, 6 is Sunday
                hour = dt.hour
                grid[dow][hour] += 1
                total_commits += 1
            except ValueError:
                continue

    peak_count = 0
    peak_day = 0
    peak_hour = 0
    for d in range(7):
        for h in range(24):
            if grid[d][h] > peak_count:
                peak_count = grid[d][h]
                peak_day = d
                peak_hour = h

    return PunchcardData(
        grid=grid,
        total_commits=total_commits,
        peak_hour=peak_hour,
        peak_day_index=peak_day,
        peak_count=peak_count,
    )
