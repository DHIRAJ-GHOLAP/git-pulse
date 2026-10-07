"""Rich terminal UI renderers for git-pulse views."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from rich.align import Align
from rich.box import ROUNDED, SIMPLE, SIMPLE_HEAVY
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from git_pulse.analyzers.audit import AuditReport
    from git_pulse.analyzers.branches import BranchReport
    from git_pulse.analyzers.changelog import ChangelogReport
    from git_pulse.analyzers.churn import ChurnData
    from git_pulse.analyzers.heatmap import HeatmapData, PunchcardData
    from git_pulse.analyzers.summary import SummaryData
from git_pulse.views.formatters import format_bytes, make_bar, truncate_text


LEVEL_CHARS = ["·", "■", "■", "■", "■"]
LEVEL_STYLES = [
    "dim #3c3c3c",   # level 0: empty
    "#0e4429",       # level 1: lowest
    "#006d32",       # level 2: medium-low
    "#26a641",       # level 3: medium-high
    "#39d353 bold",  # level 4: high
]


def render_summary(data: SummaryData, console: Console) -> None:
    """Render the main repository summary dashboard."""
    # Top Identity Panel
    title_text = Text()
    title_text.append(" ⚡ GIT-PULSE ", style="bold white on #6366f1")
    title_text.append("  ")
    title_text.append(data.repo_name, style="bold cyan")
    title_text.append("  [", style="dim")
    title_text.append(data.current_branch, style="bold green")
    title_text.append("]", style="dim")

    sub_info = []
    if data.remote_url:
        sub_info.append(f"Remote: [underline blue]{data.remote_url}[/underline blue]")
    sub_info.append(f"Path: [dim]{data.repo_path}[/dim]")
    sub_info.append(f"Default: [magenta]{data.default_branch}[/magenta]")

    panel_content = Text.from_markup(" • ".join(sub_info))
    console.print(Panel(panel_content, title=title_text, border_style="#6366f1", box=ROUNDED))

    # 3 Metrics Cards in a grid table
    grid = Table.grid(expand=True, padding=(0, 1))
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)

    # Card 1: Working Tree Status
    tree_lines = []
    if data.is_clean:
        tree_lines.append("[bold green]✔ Working tree is clean[/bold green]")
    else:
        tree_lines.append("[bold yellow]● Working tree has changes[/bold yellow]")

    tree_lines.append(f"  Staged:     [cyan]{data.staged_count}[/cyan]")
    tree_lines.append(f"  Modified:   [yellow]{data.modified_count}[/yellow]")
    tree_lines.append(f"  Untracked:  [red]{data.untracked_count}[/red]")
    tree_lines.append(f"  Stashes:    [magenta]{data.stash_count}[/magenta]")
    card1 = Panel("\n".join(tree_lines), title="[bold]Working Tree[/bold]", border_style="cyan", box=ROUNDED)

    # Card 2: 30-Day Activity
    act_lines = [
        f"Total Commits:  [bold white]{data.total_commits:,}[/bold white]",
        f"Tags:           [cyan]{len(data.tags)}[/cyan]" + (f" ([dim]{data.tags[0]}[/dim])" if data.tags else ""),
        f"Past 30 Days:   [bold green]{data.commits_last_30d}[/bold green] commits",
        f"Sparkline:      [bold #10b981]{data.activity_sparkline}[/bold #10b981]",
    ]
    card2 = Panel("\n".join(act_lines), title="[bold]Commit Pulse (30d)[/bold]", border_style="green", box=ROUNDED)

    # Card 3: Top Contributors
    contrib_lines = []
    if data.contributors:
        top_c = data.contributors[:4]
        total_c = max(1, sum(int(c["commits"]) for c in data.contributors))
        for c in top_c:
            cnt = int(c["commits"])
            pct = (cnt / total_c) * 100
            name = truncate_text(str(c["name"]), 14)
            bar = make_bar(cnt, total_c, width=8)
            contrib_lines.append(f"[bold]{name:<14}[/bold] [dim]{bar}[/dim] [cyan]{cnt:>3}[/cyan] [dim]({pct:.0f}%)[/dim]")
        if len(data.contributors) > 4:
            contrib_lines.append(f"[dim]+ {len(data.contributors) - 4} more contributor(s)[/dim]")
    else:
        contrib_lines.append("[dim]No contributor history found[/dim]")
    card3 = Panel("\n".join(contrib_lines), title=f"[bold]Contributors ({len(data.contributors)})[/bold]", border_style="magenta", box=ROUNDED)

    grid.add_row(card1, card2, card3)
    console.print(grid)

    # Recent Commits Table
    if data.recent_commits:
        rec_table = Table(title="Recent Commits", box=ROUNDED, border_style="dim", expand=True)
        rec_table.add_column("Hash", style="cyan", width=9)
        rec_table.add_column("Age", style="dim", width=12)
        rec_table.add_column("Author", style="yellow", width=18)
        rec_table.add_column("Message", style="white", ratio=1)

        for c in data.recent_commits:
            rec_table.add_row(
                c.short_hash,
                truncate_text(data.recent_commits[0].date_iso[:10] if False else c.date_iso[:10], 12),
                truncate_text(c.author_name, 18),
                truncate_text(c.subject, 70),
            )
        console.print(rec_table)
    console.print()


def render_heatmap(data: HeatmapData, console: Console) -> None:
    """Render GitHub-style contribution matrix and streak stats."""
    console.print()
    title = f" [bold white]Contribution Heatmap[/bold white] [dim]•[/dim] [cyan]Last {data.days} Days[/cyan] "
    console.print(Align.center(Panel(Text.from_markup(title), box=ROUNDED, border_style="#10b981")))

    if not data.weeks_data:
        console.print("[dim]No commit history available for heatmap.[/dim]")
        return

    # Calculate available terminal columns to adapt week columns
    term_width = console.width or 80
    day_labels_width = 5  # "Mon  "
    max_weeks_fit = max(10, (term_width - day_labels_width - 6) // 2)

    displayed_weeks = data.weeks_data[-max_weeks_fit:] if len(data.weeks_data) > max_weeks_fit else data.weeks_data

    # Month header row
    month_row = ["     "]
    prev_month = None
    for week in displayed_weeks:
        first_day_of_week = week[0][0]
        curr_month = first_day_of_week.strftime("%b")
        if curr_month != prev_month:
            month_row.append(f"[bold cyan]{curr_month[:3]}[/bold cyan]")
            prev_month = curr_month
        else:
            month_row.append("  ")

    console.print("".join(month_row))

    # 7 day rows (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun)
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for day_idx in range(7):
        row_str = []
        if day_idx in (0, 2, 4):  # Label Mon, Wed, Fri for clean look
            row_str.append(f"[dim]{day_names[day_idx]:<4}[/dim] ")
        else:
            row_str.append("     ")

        for week in displayed_weeks:
            if day_idx < len(week):
                dt, count, level = week[day_idx]
                char = LEVEL_CHARS[level]
                style = LEVEL_STYLES[level]
                row_str.append(f"[{style}]{char}[/{style}] ")
            else:
                row_str.append("  ")

        console.print("".join(row_str))

    # Legend
    legend = Text.from_markup(
        "\n     [dim]Less[/dim] "
        + " ".join(f"[{LEVEL_STYLES[i]}]{LEVEL_CHARS[i]}[/{LEVEL_STYLES[i]}]" for i in range(5))
        + " [dim]More[/dim]"
    )
    console.print(legend)

    # Streak & Stats Panel
    busiest_str = f"{data.busiest_day[0].isoformat()} ({data.busiest_day[1]} commits)" if data.busiest_day else "N/A"
    stats_table = Table.grid(expand=True, padding=(0, 2))
    stats_table.add_column()
    stats_table.add_column()
    stats_table.add_column()
    stats_table.add_column()

    stats_table.add_row(
        f"[bold]Total Commits:[/bold] [green]{data.total_commits}[/green]",
        f"[bold]Active Days:[/bold] [cyan]{data.active_days}[/cyan] / {data.days}",
        f"[bold]Current Streak:[/bold] [yellow]{data.current_streak} days[/yellow] 🔥",
        f"[bold]Longest Streak:[/bold] [magenta]{data.longest_streak} days[/magenta] 🏆",
    )
    console.print(Panel(stats_table, title="[bold]Streak & Activity Stats[/bold]", border_style="cyan", box=ROUNDED))
    console.print()


def render_punchcard(data: PunchcardData, console: Console) -> None:
    """Render 24-hour punchcard visualization."""
    console.print()
    console.print(Align.center(Panel("[bold white]Weekly Commit Punchcard (Day vs Hour)[/bold white]", box=ROUNDED, border_style="magenta")))

    # Hours Header
    header = "     " + "".join(f"{h:02d} " for h in range(24))
    console.print(f"[dim]{header}[/dim]")

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    max_c = data.peak_count or 1

    for d_idx, day_name in enumerate(day_names):
        row = [f"[bold]{day_name}[/bold]  "]
        for h in range(24):
            c = data.grid[d_idx][h]
            if c == 0:
                row.append("[dim #333333]·  [/dim #333333]")
            else:
                pct = c / max_c
                if pct > 0.7:
                    row.append(f"[bold bright_green]█  [/bold bright_green]")
                elif pct > 0.4:
                    row.append(f"[green]▓  [/green]")
                elif pct > 0.2:
                    row.append(f"[dim green]▒  [/dim green]")
                else:
                    row.append(f"[#006d32]░  [/#006d32]")
        console.print("".join(row))

    peak_day_name = day_names[data.peak_day_index]
    peak_info = (
        f"Peak Activity: [bold green]{peak_day_name} at {data.peak_hour:02d}:00[/bold green] "
        f"([cyan]{data.peak_count}[/cyan] commits) • Total commits analyzed: [bold]{data.total_commits}[/bold]"
    )
    console.print(Panel(Text.from_markup(peak_info), border_style="green", box=ROUNDED))
    console.print()


def render_churn(data: ChurnData, console: Console) -> None:
    """Render hotspot analysis and language distribution."""
    console.print()

    # Hotspots Table
    table = Table(
        title=f"🔥 Top Code Hotspots ({len(data.hotspots)} files)",
        box=ROUNDED,
        border_style="#f59e0b",
        expand=True,
    )
    table.add_column("Risk", width=8, justify="center")
    table.add_column("File Path", style="bold white", ratio=1)
    table.add_column("Commits", style="cyan", width=9, justify="right")
    table.add_column("+ Add", style="green", width=9, justify="right")
    table.add_column("- Del", style="red", width=9, justify="right")
    table.add_column("Churn", style="yellow", width=10, justify="right")

    for f in data.hotspots:
        if f.hotspot_score > 50:
            badge = "[bold red on #450a0a] HIGH [/bold red on #450a0a]"
        elif f.hotspot_score > 20:
            badge = "[bold yellow on #451a03] MED  [/bold yellow on #451a03]"
        else:
            badge = "[dim green] LOW  [/dim green]"

        table.add_row(
            badge,
            f.path + ("" if f.exists else " [dim red](deleted)[/dim red]"),
            f"{f.commits:,}",
            f"+{f.additions:,}",
            f"-{f.deletions:,}",
            f"{f.total_churn:,}",
        )

    console.print(table)

    # Language Breakdown
    if data.languages:
        lang_table = Table(
            title="Language & File Type Distribution",
            box=ROUNDED,
            border_style="cyan",
            expand=True,
        )
        lang_table.add_column("Language", style="bold cyan", width=18)
        lang_table.add_column("Files", style="white", width=8, justify="right")
        lang_table.add_column("Share", style="yellow", width=10, justify="right")
        lang_table.add_column("Distribution", ratio=1)

        for l in data.languages[:8]:
            bar = make_bar(int(l.percentage), 100, width=25)
            lang_table.add_row(
                l.language,
                f"{l.files:,}",
                f"{l.percentage:.1f}%",
                f"[#10b981]{bar}[/#10b981]",
            )
        console.print(lang_table)
    console.print()


def render_branches(report: BranchReport, console: Console) -> None:
    """Render branch list with ahead/behind and merge status."""
    console.print()

    summary_text = (
        f"Default Branch: [magenta]{report.default_branch}[/magenta] • "
        f"Active: [bold green]{report.current_branch}[/bold green] • "
        f"Merged: [cyan]{report.merged_count}[/cyan] • "
        f"Unmerged: [yellow]{report.unmerged_count}[/yellow]"
    )
    console.print(Panel(Text.from_markup(summary_text), title="[bold]Branch Overview[/bold]", border_style="cyan", box=ROUNDED))

    table = Table(box=ROUNDED, border_style="dim", expand=True)
    table.add_column("Branch", style="bold", ratio=2)
    table.add_column("Status", justify="center", width=8)
    table.add_column("Ahead/Behind", justify="center", width=14)
    table.add_column("Age", style="dim", width=10)
    table.add_column("Author", style="yellow", ratio=1)

    for b in report.branches:
        prefix = "● " if b.is_current else "  "
        branch_name = f"[bold green]{prefix}{b.name}[/bold green]" if b.is_current else f"{prefix}{b.name}"

        if b.is_default:
            status = "[magenta]Default[/magenta]"
            ab_str = "[dim]base[/dim]"
        elif b.is_merged:
            status = "[dim cyan]Merged[/dim cyan]"
            ab_str = f"+{b.ahead} / -{b.behind}"
        else:
            status = "[yellow]Active[/yellow]"
            ab_str = f"[green]+{b.ahead}[/green] / [red]-{b.behind}[/red]"

        table.add_row(
            branch_name,
            status,
            ab_str,
            b.last_commit_relative,
            truncate_text(b.last_commit_author, 18),
        )

    console.print(table)
    console.print()


def render_changelog(report: ChangelogReport, console: Console) -> None:
    """Render categorized changelog in terminal."""
    console.print()
    header = f"[bold white]Changelog: {report.version_title}[/bold white] [dim]({report.total_commits} commits)[/dim]"
    console.print(Align.center(Panel(Text.from_markup(header), border_style="#6366f1", box=ROUNDED)))

    def render_section(title: str, commits: list, color: str):
        if not commits:
            return
        t = Table(title=title, box=ROUNDED, border_style=color, expand=True)
        t.add_column("Commit", style="cyan", width=9)
        t.add_column("Scope", style="magenta", width=12)
        t.add_column("Subject", style="white", ratio=1)
        t.add_column("Author", style="dim", width=16)

        for c in commits:
            pr = f" [blue]#{c.pr_number}[/blue]" if c.pr_number else ""
            t.add_row(
                c.short_hash,
                c.scope or "-",
                f"{c.subject}{pr}",
                truncate_text(c.author, 16),
            )
        console.print(t)

    render_section("💥 Breaking Changes", report.breaking_changes, "red")
    render_section("🚀 Features", report.features, "green")
    render_section("🐛 Bug Fixes", report.bug_fixes, "yellow")
    render_section("⚡ Performance Improvements", report.performance, "cyan")
    render_section("♻️ Code Refactoring", report.refactoring, "blue")
    render_section("📝 Documentation", report.documentation, "dim")
    render_section("🔧 Tooling & Chores", report.maintenance, "dim")
    render_section("📦 Other Changes", report.other, "dim")
    console.print()


def render_audit(report: AuditReport, console: Console) -> None:
    """Render repository hygiene & security audit scorecard."""
    console.print()

    # Grade coloring
    if report.grade in ("A+", "A"):
        grade_style = "bold white on #15803d"
    elif report.grade == "B":
        grade_style = "bold black on #eab308"
    else:
        grade_style = "bold white on #b91c1c"

    score_text = Text()
    score_text.append(f" HEALTH GRADE: {report.grade} ", style=grade_style)
    score_text.append(f"  Score: {report.score}/100", style="bold white")

    console.print(Panel(score_text, title="[bold]Repository Health Scorecard[/bold]", border_style="#10b981", box=ROUNDED))

    table = Table(box=ROUNDED, border_style="dim", expand=True)
    table.add_column("Status", width=8, justify="center")
    table.add_column("Category", style="cyan", width=16)
    table.add_column("Check", style="bold white", width=28)
    table.add_column("Details & Recommendation", ratio=1)

    for f in report.findings:
        if f.status == "PASS":
            badge = "[bold green]PASS[/bold green]"
        elif f.status == "WARN":
            badge = "[bold yellow]WARN[/bold yellow]"
        else:
            badge = "[bold red]FAIL[/bold red]"

        detail = f.description
        if f.recommendation:
            detail += f"\n[dim yellow]↳ Tip: {f.recommendation}[/dim yellow]"

        table.add_row(badge, f.category, f.title, detail)

    console.print(table)
    console.print()
