"""Tests for repository audit and health scorecard."""

from pathlib import Path
from git_pulse.analyzers.audit import audit_repository
from tests.conftest import run_cmd


def test_audit_healthy_repo(sample_git_repo: Path):
    report = audit_repository(sample_git_repo)
    assert report.score >= 80
    assert report.grade in ("A+", "A")
    assert len(report.large_files) == 0
    assert len(report.sensitive_files) == 0


def test_audit_detects_sensitive_files(sample_git_repo: Path):
    env_file = sample_git_repo / ".env"
    env_file.write_text("SECRET_KEY=supersecret\n")
    run_cmd(["git", "add", ".env"], sample_git_repo)
    run_cmd(["git", "commit", "-m", "chore: add secret"], sample_git_repo)

    report = audit_repository(sample_git_repo)
    assert ".env" in report.sensitive_files
    fail_findings = [f for f in report.findings if f.status == "FAIL"]
    assert any("secret" in f.title.lower() for f in fail_findings)


def test_audit_detects_missing_license(tmp_path: Path):
    repo = tmp_path / "no_license_repo"
    repo.mkdir()
    run_cmd(["git", "init", "-b", "main"], repo)
    run_cmd(["git", "config", "user.name", "Test User"], repo)
    run_cmd(["git", "config", "user.email", "test@example.com"], repo)

    readme = repo / "README.md"
    readme.write_text("# Project\n")
    run_cmd(["git", "add", "README.md"], repo)
    run_cmd(["git", "commit", "-m", "initial"], repo)

    report = audit_repository(repo)
    warn_findings = [f for f in report.findings if f.status in ("WARN", "FAIL")]
    assert any("LICENSE" in f.title for f in warn_findings)
