"""Tests for Click CLI commands."""

from pathlib import Path
from click.testing import CliRunner
from git_pulse.cli import cli


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "git-pulse version" in result.output


def test_cli_summary(sample_git_repo: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ["summary", "-C", str(sample_git_repo)])
    assert result.exit_code == 0
    assert "GIT-PULSE" in result.output
    assert "sample_repo" in result.output


def test_cli_heatmap(sample_git_repo: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ["heatmap", "-C", str(sample_git_repo), "--days", "30"])
    assert result.exit_code == 0
    assert "Contribution Heatmap" in result.output

    # Test punchcard
    result_pc = runner.invoke(cli, ["heatmap", "-C", str(sample_git_repo), "--punchcard"])
    assert result_pc.exit_code == 0
    assert "Commit Punchcard" in result_pc.output


def test_cli_churn(sample_git_repo: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ["churn", "-C", str(sample_git_repo)])
    assert result.exit_code == 0
    assert "Code Hotspots" in result.output


def test_cli_branches(sample_git_repo: Path):
    runner = CliRunner(env={"COLUMNS": "120"})
    result = runner.invoke(cli, ["branches", "-C", str(sample_git_repo)])
    assert result.exit_code == 0
    assert "Branch Overview" in result.output
    assert "feature/awesome" in result.output


def test_cli_branches_clean(sample_git_repo: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ["branches", "clean", "-C", str(sample_git_repo)])
    assert result.exit_code == 0
    assert "feature/awesome" in result.output


def test_cli_changelog(sample_git_repo: Path, tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ["changelog", "-C", str(sample_git_repo)])
    assert result.exit_code == 0
    assert "Changelog" in result.output

    # Markdown export to file
    out_file = tmp_path / "TEST_CHANGELOG.md"
    result_export = runner.invoke(cli, ["changelog", "-C", str(sample_git_repo), "-o", str(out_file)])
    assert result_export.exit_code == 0
    assert out_file.exists()
    content = out_file.read_text()
    assert "### 🚀 Features" in content


def test_cli_audit(sample_git_repo: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ["audit", "-C", str(sample_git_repo)])
    assert result.exit_code == 0
    assert "HEALTH GRADE" in result.output


def test_cli_not_a_repo(tmp_path: Path):
    runner = CliRunner()
    non_repo = tmp_path / "empty"
    non_repo.mkdir()
    result = runner.invoke(cli, ["summary", "-C", str(non_repo)])
    assert result.exit_code == 1
    assert "Not inside a git repository" in result.output
