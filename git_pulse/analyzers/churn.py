"""Code churn, hotspot detection, and language distribution analyzer."""

from __future__ import annotations

import math
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from git_pulse import git_utils


EXTENSION_MAP = {
    ".py": "Python",
    ".pyi": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".c": "C",
    ".h": "C/C++ Header",
    ".cpp": "C++",
    ".hpp": "C/C++ Header",
    ".cc": "C++",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS/Sass",
    ".sass": "SCSS/Sass",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".xml": "XML",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".rst": "ReST",
    ".txt": "Text",
}


@dataclass
class FileChurn:
    path: str
    commits: int
    additions: int
    deletions: int
    total_churn: int
    hotspot_score: float
    exists: bool


@dataclass
class LanguageStat:
    language: str
    files: int
    percentage: float


@dataclass
class ChurnData:
    files_analyzed: int
    total_commits_analyzed: int
    hotspots: list[FileChurn]
    languages: list[LanguageStat]


def analyze_churn(
    cwd: Optional[Path | str] = None,
    limit: int = 15,
    since: Optional[str] = None,
) -> ChurnData:
    """Analyze git history to identify high-churn files and code hotspots."""
    root = git_utils.get_repo_root(cwd)
    if not root:
        raise git_utils.GitError("Not a git repository.")

    if not git_utils.has_commits(root):
        return ChurnData(
            files_analyzed=0,
            total_commits_analyzed=0,
            hotspots=[],
            languages=[],
        )

    cmd = ["log", "--numstat", "--pretty=format:COMMIT:%h"]
    if since:
        cmd.append(f"--since={since}")

    res = git_utils.run_git(cmd, cwd=root)
    file_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"commits": 0, "add": 0, "del": 0})
    total_commits = 0

    if res.returncode == 0 and res.stdout.strip():
        current_commit_files: set[str] = set()

        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue

            if line.startswith("COMMIT:"):
                total_commits += 1
                for f in current_commit_files:
                    file_stats[f]["commits"] += 1
                current_commit_files = set()
                continue

            # Format: <additions>\t<deletions>\t<filepath>
            parts = line.split("\t")
            if len(parts) == 3:
                add_str, del_str, file_path = parts
                # If binary file, git outputs "-"
                add_cnt = int(add_str) if add_str.isdigit() else 0
                del_cnt = int(del_str) if del_str.isdigit() else 0

                # Normalize path (handle renames like {old => new}/file)
                if " => " in file_path:
                    # Keep the final target path if possible
                    if "{" in file_path and "}" in file_path:
                        pre = file_path.split("{")[0]
                        mid = file_path.split("{")[1].split("}")[0]
                        post = file_path.split("}")[1]
                        target_sub = mid.split(" => ")[1]
                        file_path = f"{pre}{target_sub}{post}"
                    else:
                        file_path = file_path.split(" => ")[1]

                file_stats[file_path]["add"] += add_cnt
                file_stats[file_path]["del"] += del_cnt
                current_commit_files.add(file_path)

        for f in current_commit_files:
            file_stats[f]["commits"] += 1

    # Calculate hotspot scores
    # Formula: commits * log10(churn + 10)
    hotspots: list[FileChurn] = []
    for fpath, stats in file_stats.items():
        churn = stats["add"] + stats["del"]
        score = stats["commits"] * math.log10(churn + 10)
        full_path = root / fpath
        hotspots.append(
            FileChurn(
                path=fpath,
                commits=stats["commits"],
                additions=stats["add"],
                deletions=stats["del"],
                total_churn=churn,
                hotspot_score=score,
                exists=full_path.exists(),
            )
        )

    # Sort hotspots descending by score
    hotspots.sort(key=lambda x: x.hotspot_score, reverse=True)
    top_hotspots = hotspots[:limit]

    # Analyze language distribution from currently tracked files
    tracked = git_utils.get_tracked_files(root)
    lang_counts: dict[str, int] = defaultdict(int)
    total_tracked = len(tracked)

    for f in tracked:
        ext = os.path.splitext(f)[1].lower()
        base = os.path.basename(f).lower()
        if base in ("dockerfile", "containerfile"):
            lang = "Docker"
        elif base in ("makefile", "gnumakefile"):
            lang = "Makefile"
        elif ext in EXTENSION_MAP:
            lang = EXTENSION_MAP[ext]
        elif ext:
            lang = ext.lstrip(".").upper()
        else:
            lang = "Other"
        lang_counts[lang] += 1

    languages: list[LanguageStat] = []
    if total_tracked > 0:
        for lang, count in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total_tracked) * 100
            languages.append(LanguageStat(language=lang, files=count, percentage=pct))

    return ChurnData(
        files_analyzed=len(file_stats),
        total_commits_analyzed=total_commits,
        hotspots=top_hotspots,
        languages=languages,
    )
