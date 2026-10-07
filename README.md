# ⚡ git-pulse

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/)
[![CLI: Click + Rich](https://img.shields.io/badge/CLI-Click%20%2B%20Rich-6366f1.svg)](https://github.com/Textualize/rich)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/DHIRAJ-GHOLAP/git-pulse/pulls)

**Modern Git analytics, code churn hotspots, and developer productivity dashboard right in your terminal.**

[Installation](#-installation) •
[Quickstart](#-quickstart) •
[Features](#-features) •
[Commands](#-commands-reference) •
[Contributing](#-contributing)

</div>

---

## ✨ Overview

`git-pulse` transforms your raw Git commit history and repository metadata into rich, interactive terminal visualizations. With zero heavy external daemons or complex C dependencies, `git-pulse` gives developers, maintainers, and engineering teams instant visibility into repository health, coding habits, hotspots, and release changes.

```text
╭──────────────────────────────── ⚡ GIT-PULSE   my-project  [main] ────────────────────────────────╮
│ Remote: https://github.com/user/my-project • Path: /projects/my-project • Default: main          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
╭────── Working Tree ──────╮╭──── Commit Pulse (30d) ────╮╭────── Contributors (3) ──────╮
│ ✔ Working tree is clean  ││ Total Commits:  1,420      ││ Alice        ████████  840   │
│   Staged:     0          ││ Tags:           8 (v1.4.0) ││ Bob          ████      420   │
│   Modified:   0          ││ Past 30 Days:   48 commits ││ Charlie      █         160   │
│   Untracked:  0          ││ Sparkline:      ▂▃▄▅█▆▇▄   ││                              │
╰──────────────────────────╯╰────────────────────────────╯╰──────────────────────────────╯
```

---

## 🚀 Key Features

- 📊 **Repository Health & Summary Pulse**: Fast snapshot of working tree, stashes, 30-day activity sparkline, top contributors with visual share bars, and recent commits.
- 🟩 **GitHub-Style Contribution Heatmap**: Interactive terminal contribution grid spanning customizable timeframes (90, 180, 365 days) with active streaks, longest streak, and busiest day records.
- 🕒 **Weekly Punchcard**: 24-hour hourly distribution by day-of-the-week to visualize team cadence, peak coding hours, and weekend sprints.
- 🔥 **Code Churn & Hotspot Detection**: Pinpoint bug-prone files that change frequently and experience heavy line turnover, combined with a language/file-type breakdown.
- 🌿 **Branch Inspector & Safe Cleanup**: View branch ahead/behind status relative to the default branch; safely prune merged local branches with one command.
- 📝 **Conventional Changelog Generator**: Parses Conventional Commits into structured release notes categorized into Features, Fixes, Breaking Changes, and Performance.
- 🛡️ **Hygiene & Security Audit**: Scans for leaked secrets (`.env`, `*.pem`, `id_rsa`), bloated files (> 5MB), detached HEADs, unpushed commits, and scores repo health (A+ to F).

---

## 📦 Installation

### 1. Install via `pipx` directly from GitHub (Recommended)

`pipx` automatically manages an isolated environment and links the CLI to your PATH:

```bash
pipx install git+https://github.com/DHIRAJ-GHOLAP/git-pulse.git
```

To upgrade in the future:
```bash
pipx upgrade git-pulse
```

### 2. From Local Source

```bash
git clone https://github.com/DHIRAJ-GHOLAP/git-pulse.git
cd git-pulse

# Install CLI globally with pipx:
pipx install .

# Or develop inside an isolated virtual environment:
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## ⚡ Quickstart

Run `git-pulse` directly in any Git repository:

```bash
# Display repository overview & 30-day activity pulse
git-pulse

# View terminal contribution heatmap
git-pulse heatmap

# Discover high-risk code hotspots and language breakdown
git-pulse churn

# Check branches and ahead/behind counts
git-pulse branches

# Generate release notes from commits
git-pulse changelog

# Run repository hygiene & security health audit
git-pulse audit
```

---

## 📖 Commands Reference

### 1. `git-pulse summary` (or default `git-pulse`)
Displays the complete repository health snapshot:
```bash
git-pulse summary
# Or specify any path:
git-pulse summary -C /path/to/repo
```

### 2. `git-pulse heatmap`
Visualizes commit activity over time:
```bash
# Default: last 180 days
git-pulse heatmap

# Custom time window:
git-pulse heatmap --days 365

# Filter by author:
git-pulse heatmap --author "Dhiraj"

# Hourly punchcard view (Day vs Hour):
git-pulse heatmap --punchcard
```

### 3. `git-pulse churn`
Identifies code hotspots and file turnover:
```bash
# Top 15 hotspots:
git-pulse churn

# Customize number of files:
git-pulse churn --limit 20

# Filter time range:
git-pulse churn --since "6 months ago"
```

### 4. `git-pulse branches`
Inspects local branch states and safely cleans merged branches:
```bash
# List local branches with ahead/behind and merge status:
git-pulse branches

# Include remote tracking branches:
git-pulse branches --all

# Preview branches eligible for safe deletion (dry-run):
git-pulse branches clean

# Prune merged branches:
git-pulse branches clean --yes
```

### 5. `git-pulse changelog`
Parses Conventional Commits (`feat:`, `fix:`, `perf:`, `BREAKING CHANGE:`) into formatted release notes:
```bash
# View in terminal:
git-pulse changelog

# Specify revision range:
git-pulse changelog --from v1.0.0 --to HEAD

# Export formatted Markdown directly to CHANGELOG.md:
git-pulse changelog --output CHANGELOG.md

# Pipe Markdown to stdout:
git-pulse changelog --markdown
```

### 6. `git-pulse audit`
Scores repository hygiene and checks for common pitfalls:
```bash
# Run hygiene audit:
git-pulse audit

# Configure custom file size threshold (default 5.0 MB):
git-pulse audit --max-size 10.0
```

---

## 🛠️ Development & Testing

Clone the repository and set up the development environment:

```bash
git clone https://github.com/DHIRAJ-GHOLAP/git-pulse.git
cd git-pulse

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'feat: add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for more information.
