"""Tests for churn and language analyzer."""

from pathlib import Path
from git_pulse.analyzers.churn import analyze_churn


def test_analyze_churn_sample_repo(sample_git_repo: Path):
    churn_data = analyze_churn(sample_git_repo)
    assert churn_data.files_analyzed >= 3
    assert churn_data.total_commits_analyzed >= 4
    assert len(churn_data.hotspots) >= 1

    # Check top hotspot has positive score
    top_file = churn_data.hotspots[0]
    assert top_file.commits >= 1
    assert top_file.hotspot_score > 0

    # Language breakdown should have Python and Markdown
    lang_names = [l.language for l in churn_data.languages]
    assert "Python" in lang_names
    assert "Markdown" in lang_names


def test_analyze_churn_empty_repo(empty_git_repo: Path):
    churn_data = analyze_churn(empty_git_repo)
    assert churn_data.files_analyzed == 0
    assert churn_data.hotspots == []
