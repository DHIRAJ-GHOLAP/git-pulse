"""Pytest fixtures for git-pulse tests."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest


def run_cmd(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
    )


@pytest.fixture
def empty_git_repo(tmp_path: Path) -> Path:
    """Fixture returning an initialized git repository with 0 commits."""
    repo = tmp_path / "empty_repo"
    repo.mkdir()
    run_cmd(["git", "init", "-b", "main"], repo)
    run_cmd(["git", "config", "user.name", "Test User"], repo)
    run_cmd(["git", "config", "user.email", "test@example.com"], repo)
    return repo


@pytest.fixture
def sample_git_repo(tmp_path: Path) -> Path:
    """Fixture returning a populated git repository with commits, branches, and tags."""
    repo = tmp_path / "sample_repo"
    repo.mkdir()
    run_cmd(["git", "init", "-b", "main"], repo)
    run_cmd(["git", "config", "user.name", "Test User"], repo)
    run_cmd(["git", "config", "user.email", "test@example.com"], repo)

    # Initial commit
    readme = repo / "README.md"
    readme.write_text("# Sample Project\n\nA test project.\n")
    license_file = repo / "LICENSE"
    license_file.write_text("MIT License\n")
    gitignore = repo / ".gitignore"
    gitignore.write_text("*.pyc\n__pycache__/\n")

    run_cmd(["git", "add", "."], repo)
    run_cmd(["git", "commit", "-m", "chore: initial commit"], repo)
    run_cmd(["git", "tag", "v0.1.0"], repo)

    # Add Python file
    app = repo / "app.py"
    app.write_text("def hello():\n    return 'world'\n")
    run_cmd(["git", "add", "app.py"], repo)
    run_cmd(["git", "commit", "-m", "feat(core): add hello function (#10)"], repo)

    # Create a feature branch and merge it
    run_cmd(["git", "checkout", "-b", "feature/awesome"], repo)
    utils = repo / "utils.py"
    utils.write_text("def add(a, b):\n    return a + b\n")
    run_cmd(["git", "add", "utils.py"], repo)
    run_cmd(["git", "commit", "-m", "feat(utils): add math utils"], repo)

    # Switch back to main and merge
    run_cmd(["git", "checkout", "main"], repo)
    run_cmd(["git", "merge", "--no-ff", "feature/awesome", "-m", "Merge feature/awesome"], repo)

    # Create unmerged branch
    run_cmd(["git", "checkout", "-b", "feature/wip"], repo)
    wip = repo / "wip.txt"
    wip.write_text("work in progress\n")
    run_cmd(["git", "add", "wip.txt"], repo)
    run_cmd(["git", "commit", "-m", "feat: work in progress"], repo)

    # Return to main
    run_cmd(["git", "checkout", "main"], repo)

    # Fix commit
    app.write_text("def hello():\n    print('greeting')\n    return 'world'\n")
    run_cmd(["git", "add", "app.py"], repo)
    run_cmd(["git", "commit", "-m", "fix(core): improve hello greeting"], repo)

    return repo
