"""Tests for branch inspection and pruning."""

from pathlib import Path
from git_pulse.analyzers.branches import analyze_branches, prune_merged_branches


def test_analyze_branches_sample_repo(sample_git_repo: Path):
    report = analyze_branches(sample_git_repo)
    assert report.default_branch == "main"
    assert report.current_branch == "main"

    branch_names = [b.name for b in report.branches]
    assert "main" in branch_names
    assert "feature/awesome" in branch_names
    assert "feature/wip" in branch_names

    # Check merged status
    awesome = next(b for b in report.branches if b.name == "feature/awesome")
    assert awesome.is_merged is True

    wip = next(b for b in report.branches if b.name == "feature/wip")
    assert wip.is_merged is False


def test_prune_merged_branches(sample_git_repo: Path):
    # Dry run test
    candidates, errors = prune_merged_branches(sample_git_repo, dry_run=True)
    assert "feature/awesome" in candidates
    assert "feature/wip" not in candidates
    assert len(errors) == 0

    # Actual deletion test
    deleted, errors = prune_merged_branches(sample_git_repo, dry_run=False)
    assert "feature/awesome" in deleted
    assert len(errors) == 0

    # Ensure feature/awesome is gone
    report = analyze_branches(sample_git_repo)
    branch_names = [b.name for b in report.branches]
    assert "feature/awesome" not in branch_names
    assert "feature/wip" in branch_names
