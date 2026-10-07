"""Tests for git utility commands."""

from pathlib import Path
from git_pulse import git_utils


def test_is_git_repo(sample_git_repo: Path, tmp_path: Path):
    assert git_utils.is_git_repo(sample_git_repo) is True
    non_repo = tmp_path / "not_a_repo"
    non_repo.mkdir()
    assert git_utils.is_git_repo(non_repo) is False


def test_get_repo_root(sample_git_repo: Path):
    root = git_utils.get_repo_root(sample_git_repo)
    assert root is not None
    assert root.resolve() == sample_git_repo.resolve()


def test_has_commits(empty_git_repo: Path, sample_git_repo: Path):
    assert git_utils.has_commits(empty_git_repo) is False
    assert git_utils.has_commits(sample_git_repo) is True


def test_branch_and_default(sample_git_repo: Path):
    branch = git_utils.get_current_branch(sample_git_repo)
    assert branch == "main"
    default_b = git_utils.get_default_branch(sample_git_repo)
    assert default_b == "main"


def test_working_tree_status(sample_git_repo: Path):
    status = git_utils.get_working_tree_status(sample_git_repo)
    assert status["is_clean"] is True
    assert status["staged"] == 0
    assert status["modified"] == 0
    assert status["untracked"] == 0

    # Create untracked file
    (sample_git_repo / "new_file.txt").write_text("untracked")
    status2 = git_utils.get_working_tree_status(sample_git_repo)
    assert status2["is_clean"] is False
    assert status2["untracked"] == 1


def test_get_commit_count_and_tags(sample_git_repo: Path):
    count = git_utils.get_total_commit_count(sample_git_repo)
    assert count >= 4
    tags = git_utils.get_tags(sample_git_repo)
    assert "v0.1.0" in tags


def test_get_contributors(sample_git_repo: Path):
    contributors = git_utils.get_contributors(sample_git_repo)
    assert len(contributors) == 1
    assert contributors[0]["name"] == "Test User"
    assert contributors[0]["commits"] >= 4


def test_get_recent_commits(sample_git_repo: Path):
    commits = git_utils.get_recent_commits(limit=3, cwd=sample_git_repo)
    assert len(commits) == 3
    assert commits[0].author_name == "Test User"
