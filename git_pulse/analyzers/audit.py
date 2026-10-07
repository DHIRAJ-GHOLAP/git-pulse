"""Repository hygiene, security scanner, and health auditor."""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from git_pulse import git_utils
from git_pulse.views.formatters import format_bytes


SENSITIVE_PATTERNS = [
    ".env",
    ".env.local",
    ".env.production",
    ".env.staging",
    "*.pem",
    "*.key",
    "*.pfx",
    "*.p12",
    "id_rsa",
    "id_rsa.pub",
    "id_ed25519",
    "id_ed25519.pub",
    "*secret*.json",
    "*credentials*.json",
    "service-account*.json",
]

SENSITIVE_WHITELIST = [
    ".env.example",
    ".env.sample",
    ".env.template",
    "*.example.json",
]


@dataclass
class AuditFinding:
    category: str
    status: str  # "PASS", "WARN", "FAIL"
    title: str
    description: str
    recommendation: Optional[str] = None


@dataclass
class AuditReport:
    score: int
    grade: str
    findings: list[AuditFinding]
    large_files: list[tuple[str, int]]
    sensitive_files: list[str]


def audit_repository(cwd: Optional[Path | str] = None, max_file_size_mb: float = 5.0) -> AuditReport:
    """Run an automated hygiene and security audit on the git repository."""
    root = git_utils.get_repo_root(cwd)
    if not root:
        raise git_utils.GitError("Not a git repository.")

    findings: list[AuditFinding] = []
    penalty = 0

    # 1. Essential Repository Files
    essential_files = {
        "README": any((root / f).is_file() for f in ["README.md", "README", "README.rst"]),
        "LICENSE": any((root / f).is_file() for f in ["LICENSE", "LICENSE.md", "LICENSE.txt"]),
        ".gitignore": (root / ".gitignore").is_file(),
    }

    if essential_files["README"]:
        findings.append(AuditFinding("Repository Docs", "PASS", "README present", "Project documentation file found."))
    else:
        penalty += 10
        findings.append(AuditFinding("Repository Docs", "WARN", "Missing README", "No README.md file found.", "Add a README.md describing the project."))

    if essential_files["LICENSE"]:
        findings.append(AuditFinding("Open Source", "PASS", "License present", "Open-source license file found."))
    else:
        penalty += 10
        findings.append(AuditFinding("Open Source", "WARN", "Missing LICENSE", "No LICENSE file found.", "Add an open-source license (e.g. MIT, Apache-2.0)."))

    if essential_files[".gitignore"]:
        findings.append(AuditFinding("Cleanliness", "PASS", ".gitignore present", "Standard .gitignore file found."))
    else:
        penalty += 15
        findings.append(AuditFinding("Cleanliness", "FAIL", "Missing .gitignore", "No .gitignore file found.", "Add a .gitignore to prevent accidental commit of artifacts."))

    # 2. Tracked Files Audit (Large files & Sensitive files)
    tracked = git_utils.get_tracked_files(root)
    large_files: list[tuple[str, int]] = []
    sensitive_files: list[str] = []
    max_bytes = int(max_file_size_mb * 1024 * 1024)

    for rel_path in tracked:
        file_path = root / rel_path
        filename = file_path.name

        # Check for sensitive patterns
        is_sensitive = False
        for pattern in SENSITIVE_PATTERNS:
            if fnmatch.fnmatch(filename, pattern):
                # Check whitelist
                whitelisted = any(fnmatch.fnmatch(filename, wl) for wl in SENSITIVE_WHITELIST)
                if not whitelisted:
                    is_sensitive = True
                    break

        if is_sensitive:
            sensitive_files.append(rel_path)

        # Check file size
        try:
            if file_path.is_file():
                size = file_path.stat().st_size
                if size > max_bytes:
                    large_files.append((rel_path, size))
        except (OSError, FileNotFoundError):
            continue

    if sensitive_files:
        penalty += 35
        findings.append(
            AuditFinding(
                "Security",
                "FAIL",
                f"{len(sensitive_files)} potential secret(s) tracked",
                f"Files matching secret patterns are committed: {', '.join(sensitive_files[:3])}",
                "Remove sensitive files with git rm --cached and add them to .gitignore.",
            )
        )
    else:
        findings.append(AuditFinding("Security", "PASS", "No exposed secret files tracked", "No known secret files found in tracked files."))

    if large_files:
        penalty += 15
        findings.append(
            AuditFinding(
                "Performance",
                "WARN",
                f"{len(large_files)} large file(s) (> {max_file_size_mb} MB) tracked",
                f"Largest file: {large_files[0][0]} ({format_bytes(large_files[0][1])})",
                "Consider using Git LFS or moving large assets to external storage.",
            )
        )
    else:
        findings.append(AuditFinding("Performance", "PASS", f"No bloated files (> {max_file_size_mb} MB)", "Tracked files are within healthy size limits."))

    # 3. Working Tree Status
    status = git_utils.get_working_tree_status(root)
    if status["is_clean"]:
        findings.append(AuditFinding("Working Tree", "PASS", "Clean working tree", "No uncommitted or untracked changes."))
    else:
        dirty_details = []
        if status["staged"]:
            dirty_details.append(f"{status['staged']} staged")
        if status["modified"]:
            dirty_details.append(f"{status['modified']} modified")
        if status["untracked"]:
            dirty_details.append(f"{status['untracked']} untracked")
        findings.append(
            AuditFinding(
                "Working Tree",
                "WARN",
                "Uncommitted changes present",
                ", ".join(dirty_details),
                "Commit or stash working changes to keep history clean.",
            )
        )

    # 4. Stashes
    stash_cnt = git_utils.get_stash_count(root)
    if stash_cnt > 5:
        penalty += 5
        findings.append(
            AuditFinding(
                "Hygiene",
                "WARN",
                f"{stash_cnt} stashes accumulated",
                "High number of old stashes in repository.",
                "Review and prune stashes using 'git stash drop' or 'git stash clear'.",
            )
        )
    else:
        findings.append(AuditFinding("Hygiene", "PASS", f"Stash count healthy ({stash_cnt})", "Few or no stashes accumulated."))

    # 5. Branch State
    curr_branch = git_utils.get_current_branch(root)
    if curr_branch.startswith("(detached"):
        penalty += 15
        findings.append(
            AuditFinding(
                "Git State",
                "FAIL",
                "Detached HEAD",
                "Repository is in a detached HEAD state.",
                "Switch back to a named branch using 'git checkout <branch>'.",
            )
        )
    else:
        findings.append(AuditFinding("Git State", "PASS", f"Active on branch '{curr_branch}'", "Working on a named branch."))

    # 6. Remote Tracking & Unpushed commits
    if git_utils.has_commits(root) and not curr_branch.startswith("("):
        upstream_chk = git_utils.run_git(["rev-parse", "--abbrev-ref", f"{curr_branch}@{{u}}"], cwd=root)
        if upstream_chk.returncode != 0:
            findings.append(
                AuditFinding(
                    "Remote Sync",
                    "WARN",
                    "No upstream branch configured",
                    f"Branch '{curr_branch}' does not have a tracking remote.",
                    f"Set upstream via 'git push -u origin {curr_branch}'.",
                )
            )
        else:
            unpushed = git_utils.run_git(["log", "@{u}..HEAD", "--oneline"], cwd=root)
            if unpushed.returncode == 0 and unpushed.stdout.strip():
                cnt = len(unpushed.stdout.strip().splitlines())
                findings.append(
                    AuditFinding(
                        "Remote Sync",
                        "WARN",
                        f"{cnt} unpushed commit(s)",
                        "Local commits have not yet been pushed to remote.",
                        "Push commits to remote with 'git push'.",
                    )
                )
            else:
                findings.append(AuditFinding("Remote Sync", "PASS", "In sync with remote", "All local commits pushed to remote."))

    score = max(0, 100 - penalty)
    if score >= 90:
        grade = "A+"
    elif score >= 80:
        grade = "A"
    elif score >= 70:
        grade = "B"
    elif score >= 50:
        grade = "C"
    else:
        grade = "F"

    return AuditReport(
        score=score,
        grade=grade,
        findings=findings,
        large_files=large_files,
        sensitive_files=sensitive_files,
    )
