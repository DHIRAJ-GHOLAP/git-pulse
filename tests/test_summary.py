"""Tests for summary analyzer."""

from pathlib import Path
from git_pulse.analyzers.summary import analyze_summary


def test_analyze_summary_sample_repo(sample_git_repo: Path):
    data = analyze_summary(sample_git_repo)
    assert data.repo_name == "sample_repo"
    assert data.current_branch == "main"
    assert data.total_commits >= 4
    assert len(data.tags) >= 1
    assert data.commits_last_30d >= 4
    assert len(data.activity_30d) == 30
    assert len(data.contributors) == 1


def test_analyze_summary_empty_repo(empty_git_repo: Path):
    data = analyze_summary(empty_git_repo)
    assert data.repo_name == "empty_repo"
    assert data.total_commits == 0
    assert data.commits_last_30d == 0
