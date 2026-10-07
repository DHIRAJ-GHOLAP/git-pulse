"""Tests for heatmap and punchcard analyzers."""

from pathlib import Path
from git_pulse.analyzers.heatmap import analyze_heatmap, analyze_punchcard


def test_analyze_heatmap_sample_repo(sample_git_repo: Path):
    h_data = analyze_heatmap(sample_git_repo, num_days=30)
    assert h_data.total_commits >= 4
    assert h_data.active_days >= 1
    assert h_data.current_streak >= 1
    assert len(h_data.weeks_data) > 0


def test_analyze_heatmap_empty_repo(empty_git_repo: Path):
    h_data = analyze_heatmap(empty_git_repo, num_days=30)
    assert h_data.total_commits == 0
    assert h_data.active_days == 0
    assert h_data.current_streak == 0


def test_analyze_punchcard_sample_repo(sample_git_repo: Path):
    p_data = analyze_punchcard(sample_git_repo)
    assert p_data.total_commits >= 4
    assert len(p_data.grid) == 7
    assert len(p_data.grid[0]) == 24
    assert p_data.peak_count >= 1
