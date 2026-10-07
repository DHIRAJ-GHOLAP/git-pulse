"""Repository overview and 30-day activity summary analyzer."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from git_pulse import git_utils
from git_pulse.views.formatters import generate_sparkline


@dataclass
class SummaryData:
    repo_name: str
    repo_path: Path
    current_branch: str
    default_branch: str
    remote_url: Optional[str]
    is_clean: bool
    staged_count: int
    modified_count: int
    untracked_count: int
    stash_count: int
    total_commits: int
    tags: list[str]
    contributors: list[dict[str, str | int]]
    recent_commits: list[git_utils.CommitInfo]
    activity_30d: list[int]
    activity_sparkline: str
    commits_last_30d: int


def analyze_summary(cwd: Optional[Path | str] = None) -> SummaryData:
    """Gather complete summary information for the current git repository."""
    root = git_utils.get_repo_root(cwd)
    if not root:
        raise git_utils.GitError("Not a git repository.")

    repo_name = root.name
    branch = git_utils.get_current_branch(root)
    default_branch = git_utils.get_default_branch(root)
    remote = git_utils.get_remote_url(root)

    status = git_utils.get_working_tree_status(root)
    stashes = git_utils.get_stash_count(root)
    total_commits = git_utils.get_total_commit_count(root)
    tags = git_utils.get_tags(root)
    contributors = git_utils.get_contributors(root)
    recent = git_utils.get_recent_commits(limit=5, cwd=root)

    # 30-day activity calculation
    activity_30d = [0] * 30
    commits_last_30d = 0
    if total_commits > 0:
        # Get commit timestamps from the last 30 days
        since_ts = int(time.time() - 30 * 86400)
        res = git_utils.run_git(
            ["log", f"--since={since_ts}", "--format=%ct"],
            cwd=root,
        )
        if res.returncode == 0 and res.stdout.strip():
            now = time.time()
            for line in res.stdout.strip().splitlines():
                try:
                    ts = int(line.strip())
                    days_ago = int((now - ts) // 86400)
                    if 0 <= days_ago < 30:
                        # Index 29 is today, Index 0 is 29 days ago
                        idx = 29 - days_ago
                        activity_30d[idx] += 1
                        commits_last_30d += 1
                except ValueError:
                    continue

    sparkline = generate_sparkline(activity_30d)

    return SummaryData(
        repo_name=repo_name,
        repo_path=root,
        current_branch=branch,
        default_branch=default_branch,
        remote_url=remote,
        is_clean=status["is_clean"],  # type: ignore
        staged_count=status["staged"],  # type: ignore
        modified_count=status["modified"],  # type: ignore
        untracked_count=status["untracked"],  # type: ignore
        stash_count=stashes,
        total_commits=total_commits,
        tags=tags,
        contributors=contributors,
        recent_commits=recent,
        activity_30d=activity_30d,
        activity_sparkline=sparkline,
        commits_last_30d=commits_last_30d,
    )
