"""Git utility functions leveraging the standard git CLI."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class GitError(Exception):
    """Raised when a git operation fails."""
    pass


def run_git(
    args: list[str],
    cwd: Optional[Path | str] = None,
    check: bool = False,
    timeout: int = 30,
) -> subprocess.CompletedProcess[str]:
    """Execute a git command with timeout and safety guarantees."""
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=check,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise GitError("git is not installed or not in PATH.")
    except subprocess.TimeoutExpired:
        raise GitError(f"git command timed out after {timeout}s: git {' '.join(args)}")
    except subprocess.CalledProcessError as e:
        raise GitError(f"git command failed: {e.stderr.strip() or e.stdout.strip()}")


def is_git_repo(path: Optional[Path | str] = None) -> bool:
    """Return True if path is within a git repository."""
    res = run_git(["rev-parse", "--is-inside-work-tree"], cwd=path)
    return res.returncode == 0 and res.stdout.strip() == "true"


def get_repo_root(path: Optional[Path | str] = None) -> Optional[Path]:
    """Return the absolute path to the root of the current git repository."""
    res = run_git(["rev-parse", "--show-toplevel"], cwd=path)
    if res.returncode == 0:
        return Path(res.stdout.strip())
    return None


def has_commits(cwd: Optional[Path | str] = None) -> bool:
    """Return True if the repository has at least one commit."""
    res = run_git(["rev-parse", "--verify", "HEAD"], cwd=cwd)
    return res.returncode == 0


def get_current_branch(cwd: Optional[Path | str] = None) -> str:
    """Return the current branch name, or '(detached)' if in detached HEAD state."""
    res = run_git(["symbolic-ref", "--short", "HEAD"], cwd=cwd)
    if res.returncode == 0:
        return res.stdout.strip()
    
    # Detached HEAD fallback
    short_hash = run_git(["rev-parse", "--short", "HEAD"], cwd=cwd)
    if short_hash.returncode == 0:
        return f"(detached: {short_hash.stdout.strip()})"
    return "(empty repo)"


def get_default_branch(cwd: Optional[Path | str] = None) -> str:
    """Detect the repository's default branch (main, master, etc.)."""
    # Try origin/HEAD
    res = run_git(["symbolic-ref", "refs/remotes/origin/HEAD"], cwd=cwd)
    if res.returncode == 0:
        ref = res.stdout.strip()
        return ref.split("/")[-1]

    # Test common default branch names
    for candidate in ["main", "master", "trunk", "development"]:
        chk = run_git(["rev-parse", "--verify", f"refs/heads/{candidate}"], cwd=cwd)
        if chk.returncode == 0:
            return candidate

    return "main"


def get_remote_url(cwd: Optional[Path | str] = None, remote_name: str = "origin") -> Optional[str]:
    """Return the fetch URL for the specified remote."""
    res = run_git(["remote", "get-url", remote_name], cwd=cwd)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip()
    return None


def get_working_tree_status(cwd: Optional[Path | str] = None) -> dict[str, int | bool]:
    """Return status summary: staged, modified, untracked, and is_clean."""
    res = run_git(["status", "--porcelain=v1"], cwd=cwd)
    if res.returncode != 0:
        return {"staged": 0, "modified": 0, "untracked": 0, "is_clean": True}

    staged = 0
    modified = 0
    untracked = 0

    for line in res.stdout.splitlines():
        if len(line) < 2:
            continue
        index_status = line[0]
        worktree_status = line[1]

        if index_status == "?" and worktree_status == "?":
            untracked += 1
            continue

        if index_status in "MADRC":
            staged += 1
        if worktree_status in "MD":
            modified += 1

    is_clean = (staged == 0 and modified == 0 and untracked == 0)
    return {
        "staged": staged,
        "modified": modified,
        "untracked": untracked,
        "is_clean": is_clean,
    }


def get_stash_count(cwd: Optional[Path | str] = None) -> int:
    """Return the number of stashes saved."""
    res = run_git(["stash", "list"], cwd=cwd)
    if res.returncode == 0 and res.stdout.strip():
        return len(res.stdout.strip().splitlines())
    return 0


def get_total_commit_count(cwd: Optional[Path | str] = None) -> int:
    """Return total number of commits reachable from HEAD."""
    if not has_commits(cwd):
        return 0
    res = run_git(["rev-list", "--count", "HEAD"], cwd=cwd)
    if res.returncode == 0:
        try:
            return int(res.stdout.strip())
        except ValueError:
            return 0
    return 0


def get_tags(cwd: Optional[Path | str] = None) -> list[str]:
    """Return list of tags ordered by creator date descending."""
    res = run_git(["tag", "--list", "--sort=-creatordate"], cwd=cwd)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip().splitlines()
    return []


@dataclass
class CommitInfo:
    hash: str
    short_hash: str
    author_name: str
    author_email: str
    timestamp: int
    date_iso: str
    subject: str


def get_recent_commits(limit: int = 5, cwd: Optional[Path | str] = None) -> list[CommitInfo]:
    """Return recent commits with metadata."""
    if not has_commits(cwd):
        return []

    format_str = "%H%x1f%h%x1f%an%x1f%ae%x1f%ct%x1f%aI%x1f%s"
    res = run_git(["log", f"-n{limit}", f"--format={format_str}"], cwd=cwd)
    if res.returncode != 0 or not res.stdout.strip():
        return []

    commits: list[CommitInfo] = []
    for line in res.stdout.strip().splitlines():
        parts = line.split("\x1f")
        if len(parts) == 7:
            try:
                commits.append(
                    CommitInfo(
                        hash=parts[0],
                        short_hash=parts[1],
                        author_name=parts[2],
                        author_email=parts[3],
                        timestamp=int(parts[4]),
                        date_iso=parts[5],
                        subject=parts[6],
                    )
                )
            except ValueError:
                continue
    return commits


def get_contributors(cwd: Optional[Path | str] = None) -> list[dict[str, str | int]]:
    """Return contributor statistics sorted by commit count descending."""
    if not has_commits(cwd):
        return []

    res = run_git(["shortlog", "-sne", "--all"], cwd=cwd)
    if res.returncode != 0 or not res.stdout.strip():
        return []

    contributors = []
    for line in res.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        # Format: "<count>\t<name> <<email>>"
        try:
            count_str, author_info = line.split("\t", 1)
            count = int(count_str.strip())
            if "<" in author_info and author_info.endswith(">"):
                name, email = author_info.rsplit("<", 1)
                name = name.strip()
                email = email[:-1].strip()
            else:
                name = author_info.strip()
                email = ""
            contributors.append({"name": name, "email": email, "commits": count})
        except Exception:
            continue

    return contributors


def get_tracked_files(cwd: Optional[Path | str] = None) -> list[str]:
    """Return list of all files currently tracked by git."""
    res = run_git(["ls-files"], cwd=cwd)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip().splitlines()
    return []
