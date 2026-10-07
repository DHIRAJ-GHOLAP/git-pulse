"""Tests for Conventional Commits parser and changelog generator."""

from pathlib import Path
from git_pulse.analyzers.changelog import (
    generate_changelog,
    parse_commit_message,
    render_markdown_changelog,
)


def test_parse_commit_message_conventional():
    parsed = parse_commit_message(
        commit_hash="abcdef123456",
        short_hash="abcdef1",
        author="Alice",
        subject="feat(auth): add OAuth2 login flow (#42)",
        body="",
    )
    assert parsed.commit_type == "feat"
    assert parsed.scope == "auth"
    assert parsed.subject == "add OAuth2 login flow"
    assert parsed.pr_number == "42"
    assert parsed.is_breaking is False


def test_parse_commit_message_breaking_bang():
    parsed = parse_commit_message(
        commit_hash="123456abcdef",
        short_hash="123456a",
        author="Bob",
        subject="feat(api)!: remove deprecated v1 endpoints",
        body="",
    )
    assert parsed.commit_type == "feat"
    assert parsed.is_breaking is True


def test_parse_commit_message_breaking_body():
    parsed = parse_commit_message(
        commit_hash="7890abcdef12",
        short_hash="7890abc",
        author="Charlie",
        subject="fix: update config file schema",
        body="BREAKING CHANGE: old config key 'url' is now renamed to 'endpoint'",
    )
    assert parsed.commit_type == "fix"
    assert parsed.is_breaking is True
    assert parsed.breaking_description == "old config key 'url' is now renamed to 'endpoint'"


def test_generate_changelog_sample_repo(sample_git_repo: Path):
    report = generate_changelog(sample_git_repo, limit=10)
    assert report.total_commits >= 4
    assert len(report.features) >= 1
    assert len(report.bug_fixes) >= 1

    md = render_markdown_changelog(report)
    assert "### 🚀 Features" in md
    assert "### 🐛 Bug Fixes" in md
    assert "add hello function" in md
