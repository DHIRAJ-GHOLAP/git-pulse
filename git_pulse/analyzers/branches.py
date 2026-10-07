"""Branch analytics and merged branch cleanup analyzer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from git_pulse import git_utils
from git_pulse.views.formatters import relative_time


@dataclass
class BranchDetail:
    name: str
    is_current: bool
    is_default: bool
    is_merged: bool
    ahead: int
    behind: int
    last_commit_hash: str
    last_commit_subject: str
    last_commit_author: str
    last_commit_timestamp: int
    last_commit_relative: str


@dataclass
class BranchReport:
    default_branch: str
    current_branch: str
    branches: list[BranchDetail]
    merged_count: int
    unmerged_count: int


def analyze_branches(cwd: Optional[Path | str] = None, include_remotes: bool = False) -> BranchReport:
    """Analyze all local branches, their ahead/behind status, and merge state."""
    root = git_utils.get_repo_root(cwd)
    if not root:
        raise git_utils.GitError("Not a git repository.")

    default_branch = git_utils.get_default_branch(root)
    current_branch = git_utils.get_current_branch(root)

    if not git_utils.has_commits(root):
        return BranchReport(
            default_branch=default_branch,
            current_branch=current_branch,
            branches=[],
            merged_count=0,
            unmerged_count=0,
        )

    # Get merged branches relative to default branch
    merged_res = git_utils.run_git(["branch", "--merged", default_branch], cwd=root)
    merged_branches: set[str] = set()
    if merged_res.returncode == 0:
        for line in merged_res.stdout.splitlines():
            name = line.strip().lstrip("* ").strip()
            if name:
                merged_branches.add(name)

    # List local branches with format
    # %(refname:short)|%(objectname:short)|%(committerdate:raw)|%(authorname)|%(subject)
    cmd = [
        "for-each-ref",
        "--format=%(refname:short)|%(objectname:short)|%(committerdate:raw)|%(authorname)|%(subject)",
        "refs/heads/",
    ]
    if include_remotes:
        cmd.append("refs/remotes/origin/")

    res = git_utils.run_git(cmd, cwd=root)
    branches: list[BranchDetail] = []
    merged_count = 0
    unmerged_count = 0

    if res.returncode == 0 and res.stdout.strip():
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("|", 4)
            if len(parts) < 5:
                continue

            ref_name, short_hash, raw_date, author, subject = parts
            clean_name = ref_name.replace("origin/", "") if ref_name.startswith("origin/") else ref_name

            # Skip HEAD symref if in remotes
            if clean_name == "HEAD":
                continue

            try:
                timestamp = int(raw_date.split()[0])
            except (ValueError, IndexError):
                timestamp = 0

            is_curr = (ref_name == current_branch or clean_name == current_branch)
            is_def = (ref_name == default_branch or clean_name == default_branch)
            is_mrg = (ref_name in merged_branches or clean_name in merged_branches)

            if not is_def:
                if is_mrg:
                    merged_count += 1
                else:
                    unmerged_count += 1

            # Compute ahead/behind relative to default branch
            ahead = 0
            behind = 0
            if not is_def:
                rev_cnt = git_utils.run_git(
                    ["rev-list", "--left-right", "--count", f"{default_branch}...{ref_name}"],
                    cwd=root,
                )
                if rev_cnt.returncode == 0 and rev_cnt.stdout.strip():
                    try:
                        b_str, a_str = rev_cnt.stdout.strip().split()
                        behind = int(b_str)
                        ahead = int(a_str)
                    except ValueError:
                        pass

            branches.append(
                BranchDetail(
                    name=ref_name,
                    is_current=is_curr,
                    is_default=is_def,
                    is_merged=is_mrg,
                    ahead=ahead,
                    behind=behind,
                    last_commit_hash=short_hash,
                    last_commit_subject=subject,
                    last_commit_author=author,
                    last_commit_timestamp=timestamp,
                    last_commit_relative=relative_time(timestamp),
                )
            )

    # Sort: current branch first, then default branch, then by commit timestamp descending
    branches.sort(
        key=lambda b: (
            not b.is_current,
            not b.is_default,
            -b.last_commit_timestamp,
        )
    )

    return BranchReport(
        default_branch=default_branch,
        current_branch=current_branch,
        branches=branches,
        merged_count=merged_count,
        unmerged_count=unmerged_count,
    )


def prune_merged_branches(
    cwd: Optional[Path | str] = None,
    dry_run: bool = True,
) -> tuple[list[str], list[str]]:
    """Find and optionally delete local branches that have been merged into default."""
    report = analyze_branches(cwd=cwd, include_remotes=False)
    candidates = [
        b.name
        for b in report.branches
        if b.is_merged and not b.is_default and not b.is_current
    ]

    deleted: list[str] = []
    errors: list[str] = []

    if not dry_run and candidates:
        root = git_utils.get_repo_root(cwd)
        for name in candidates:
            res = git_utils.run_git(["branch", "-d", name], cwd=root)
            if res.returncode == 0:
                deleted.append(name)
            else:
                errors.append(f"{name}: {res.stderr.strip()}")
    else:
        deleted = candidates

    return deleted, errors
