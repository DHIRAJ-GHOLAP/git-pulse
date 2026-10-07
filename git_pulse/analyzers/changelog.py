"""Conventional Commits parser and GitHub release notes / changelog generator."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from git_pulse import git_utils


CONVENTIONAL_REGEX = re.compile(
    r"^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<subject>.+)$"
)
PR_REGEX = re.compile(r"\(#(\d+)\)|#(\d+)")


@dataclass
class ParsedCommit:
    hash: str
    short_hash: str
    author: str
    raw_subject: str
    commit_type: str
    scope: Optional[str]
    subject: str
    is_breaking: bool
    breaking_description: Optional[str] = None
    pr_number: Optional[str] = None


@dataclass
class ChangelogReport:
    version_title: str
    from_ref: Optional[str]
    to_ref: str
    total_commits: int
    breaking_changes: list[ParsedCommit] = field(default_factory=list)
    features: list[ParsedCommit] = field(default_factory=list)
    bug_fixes: list[ParsedCommit] = field(default_factory=list)
    performance: list[ParsedCommit] = field(default_factory=list)
    refactoring: list[ParsedCommit] = field(default_factory=list)
    documentation: list[ParsedCommit] = field(default_factory=list)
    maintenance: list[ParsedCommit] = field(default_factory=list)
    other: list[ParsedCommit] = field(default_factory=list)


def parse_commit_message(
    commit_hash: str,
    short_hash: str,
    author: str,
    subject: str,
    body: str = "",
) -> ParsedCommit:
    """Parse a single commit message according to Conventional Commits specification."""
    subject = subject.strip()
    match = CONVENTIONAL_REGEX.match(subject)

    pr_match = PR_REGEX.search(subject)
    pr_num = (pr_match.group(1) or pr_match.group(2)) if pr_match else None

    # Check for breaking change markers in body
    is_breaking = False
    breaking_desc = None
    if "BREAKING CHANGE:" in body or "BREAKING-CHANGE:" in body:
        is_breaking = True
        for line in body.splitlines():
            if "BREAKING CHANGE:" in line or "BREAKING-CHANGE:" in line:
                breaking_desc = line.split(":", 1)[1].strip()
                break

    if match:
        c_type = match.group("type").lower()
        scope = match.group("scope")
        if match.group("breaking") == "!":
            is_breaking = True
        clean_subject = match.group("subject").strip()
        if pr_match:
            clean_subject = PR_REGEX.sub("", clean_subject).strip()

        return ParsedCommit(
            hash=commit_hash,
            short_hash=short_hash,
            author=author,
            raw_subject=subject,
            commit_type=c_type,
            scope=scope,
            subject=clean_subject,
            is_breaking=is_breaking,
            breaking_description=breaking_desc,
            pr_number=pr_num,
        )

    return ParsedCommit(
        hash=commit_hash,
        short_hash=short_hash,
        author=author,
        raw_subject=subject,
        commit_type="other",
        scope=None,
        subject=subject,
        is_breaking=is_breaking,
        breaking_description=breaking_desc,
        pr_number=pr_num,
    )


def generate_changelog(
    cwd: Optional[Path | str] = None,
    from_ref: Optional[str] = None,
    to_ref: str = "HEAD",
    limit: int = 50,
) -> ChangelogReport:
    """Generate categorized changelog between two git revisions or from latest tag."""
    root = git_utils.get_repo_root(cwd)
    if not root:
        raise git_utils.GitError("Not a git repository.")

    if not git_utils.has_commits(root):
        return ChangelogReport(
            version_title="Unreleased",
            from_ref=None,
            to_ref=to_ref,
            total_commits=0,
        )

    # If from_ref not specified, try to find the latest tag
    if not from_ref:
        tags = git_utils.get_tags(root)
        if tags:
            from_ref = tags[0]

    # Build git log range
    format_str = "%H%x1f%h%x1f%an%x1f%s%x1f%b%x1e"
    cmd = ["log", f"--format={format_str}"]
    if from_ref:
        cmd.append(f"{from_ref}..{to_ref}")
        version_title = f"{to_ref} (since {from_ref})"
    else:
        cmd.append(f"-n{limit}")
        cmd.append(to_ref)
        version_title = f"Recent Commits ({to_ref})"

    res = git_utils.run_git(cmd, cwd=root)
    report = ChangelogReport(
        version_title=version_title,
        from_ref=from_ref,
        to_ref=to_ref,
        total_commits=0,
    )

    if res.returncode != 0 or not res.stdout.strip():
        return report

    raw_commits = res.stdout.strip().split("\x1e")
    for entry in raw_commits:
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split("\x1f")
        if len(parts) >= 4:
            c_hash, s_hash, author, subject = parts[:4]
            body = parts[4] if len(parts) > 4 else ""
            parsed = parse_commit_message(c_hash, s_hash, author, subject, body)
            report.total_commits += 1

            if parsed.is_breaking:
                report.breaking_changes.append(parsed)

            if parsed.commit_type == "feat":
                report.features.append(parsed)
            elif parsed.commit_type == "fix":
                report.bug_fixes.append(parsed)
            elif parsed.commit_type == "perf":
                report.performance.append(parsed)
            elif parsed.commit_type == "refactor":
                report.refactoring.append(parsed)
            elif parsed.commit_type == "docs":
                report.documentation.append(parsed)
            elif parsed.commit_type in ("chore", "build", "ci", "test", "style"):
                report.maintenance.append(parsed)
            else:
                report.other.append(parsed)

    return report


def render_markdown_changelog(report: ChangelogReport) -> str:
    """Format ChangelogReport into clean GitHub Flavored Markdown."""
    lines: list[str] = []
    lines.append(f"## {report.version_title}\n")

    if report.total_commits == 0:
        lines.append("*No commits found in this range.*\n")
        return "\n".join(lines)

    def format_item(c: ParsedCommit) -> str:
        scope_prefix = f"**{c.scope}:** " if c.scope else ""
        pr_suffix = f" (#{c.pr_number})" if c.pr_number else ""
        return f"- {scope_prefix}{c.subject}{pr_suffix} (`{c.short_hash}` by @{c.author})"

    if report.breaking_changes:
        lines.append("### 💥 Breaking Changes\n")
        for c in report.breaking_changes:
            desc = f" - {c.breaking_description}" if c.breaking_description else ""
            lines.append(f"{format_item(c)}{desc}")
        lines.append("")

    if report.features:
        lines.append("### 🚀 Features\n")
        for c in report.features:
            lines.append(format_item(c))
        lines.append("")

    if report.bug_fixes:
        lines.append("### 🐛 Bug Fixes\n")
        for c in report.bug_fixes:
            lines.append(format_item(c))
        lines.append("")

    if report.performance:
        lines.append("### ⚡ Performance Improvements\n")
        for c in report.performance:
            lines.append(format_item(c))
        lines.append("")

    if report.refactoring:
        lines.append("### ♻️ Code Refactoring\n")
        for c in report.refactoring:
            lines.append(format_item(c))
        lines.append("")

    if report.documentation:
        lines.append("### 📝 Documentation\n")
        for c in report.documentation:
            lines.append(format_item(c))
        lines.append("")

    if report.maintenance:
        lines.append("### 🔧 Tooling & Chores\n")
        for c in report.maintenance:
            lines.append(format_item(c))
        lines.append("")

    if report.other:
        lines.append("### 📦 Other Changes\n")
        for c in report.other:
            lines.append(format_item(c))
        lines.append("")

    return "\n".join(lines)
