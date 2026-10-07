"""Command Line Interface for git-pulse."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from git_pulse import __version__
from git_pulse.analyzers.audit import audit_repository
from git_pulse.analyzers.branches import analyze_branches, prune_merged_branches
from git_pulse.analyzers.changelog import generate_changelog, render_markdown_changelog
from git_pulse.analyzers.churn import analyze_churn
from git_pulse.analyzers.heatmap import analyze_heatmap, analyze_punchcard
from git_pulse.analyzers.summary import analyze_summary
from git_pulse.git_utils import GitError, is_git_repo
from git_pulse.views.renderer import (
    render_audit,
    render_branches,
    render_changelog,
    render_churn,
    render_heatmap,
    render_punchcard,
    render_summary,
)

console = Console()


def verify_repo_or_exit(path: Optional[Path | str] = None) -> None:
    """Ensure current directory or path is inside a git repository."""
    if not is_git_repo(path):
        console.print("[bold red]Error:[/bold red] Not inside a git repository.", style="red")
        console.print("[dim]Navigate into a git repository or run 'git init' to get started.[/dim]")
        sys.exit(1)


@click.group(invoke_without_command=True)
@click.option("--version", "-v", is_flag=True, help="Show git-pulse version and exit.")
@click.option("--path", "-C", type=click.Path(exists=True, file_okay=False, path_type=Path), help="Run as if git was started in <path>.")
@click.pass_context
def cli(ctx: click.Context, version: bool, path: Optional[Path]) -> None:
    """⚡ git-pulse: Modern Git analytics & developer productivity dashboard."""
    if version:
        console.print(f"[bold cyan]git-pulse[/bold cyan] version [green]{__version__}[/green]")
        sys.exit(0)

    ctx.ensure_object(dict)
    ctx.obj["PATH"] = path

    if ctx.invoked_subcommand is None:
        ctx.invoke(summary, path=path)


@cli.command("summary")
@click.option("--path", "-C", type=click.Path(exists=True, file_okay=False, path_type=Path), help="Repository directory.")
def summary(path: Optional[Path]) -> None:
    """Display comprehensive repository overview & 30-day activity pulse."""
    target_path = path or click.get_current_context().obj.get("PATH")
    verify_repo_or_exit(target_path)
    try:
        data = analyze_summary(cwd=target_path)
        render_summary(data, console)
    except GitError as e:
        console.print(f"[bold red]Git Error:[/bold red] {e}")
        sys.exit(1)


@cli.command("heatmap")
@click.option("--days", "-d", default=180, show_default=True, type=int, help="Number of past days to display.")
@click.option("--author", "-a", type=str, default=None, help="Filter commits by author name or email.")
@click.option("--punchcard", "-p", is_flag=True, help="Display 24-hour weekly punchcard grid instead of calendar.")
@click.option("--path", "-C", type=click.Path(exists=True, file_okay=False, path_type=Path), help="Repository directory.")
def heatmap(days: int, author: Optional[str], punchcard: bool, path: Optional[Path]) -> None:
    """Visualize GitHub-style contribution matrix or weekly hourly punchcard."""
    target_path = path or click.get_current_context().obj.get("PATH")
    verify_repo_or_exit(target_path)
    try:
        if punchcard:
            p_data = analyze_punchcard(cwd=target_path, author=author)
            render_punchcard(p_data, console)
        else:
            h_data = analyze_heatmap(cwd=target_path, num_days=days, author=author)
            render_heatmap(h_data, console)
    except GitError as e:
        console.print(f"[bold red]Git Error:[/bold red] {e}")
        sys.exit(1)


@cli.command("churn")
@click.option("--limit", "-n", default=15, show_default=True, type=int, help="Number of hotspot files to show.")
@click.option("--since", "-s", type=str, default=None, help="Analyze history since date (e.g. '30 days ago', '6 months ago').")
@click.option("--path", "-C", type=click.Path(exists=True, file_okay=False, path_type=Path), help="Repository directory.")
def churn(limit: int, since: Optional[str], path: Optional[Path]) -> None:
    """Detect code churn hotspots and language distribution."""
    target_path = path or click.get_current_context().obj.get("PATH")
    verify_repo_or_exit(target_path)
    try:
        data = analyze_churn(cwd=target_path, limit=limit, since=since)
        render_churn(data, console)
    except GitError as e:
        console.print(f"[bold red]Git Error:[/bold red] {e}")
        sys.exit(1)


@cli.group("branches", invoke_without_command=True)
@click.option("--all", "-a", "include_remotes", is_flag=True, help="Include remote tracking branches.")
@click.option("--path", "-C", type=click.Path(exists=True, file_okay=False, path_type=Path), help="Repository directory.")
@click.pass_context
def branches(ctx: click.Context, include_remotes: bool, path: Optional[Path]) -> None:
    """Inspect branch ahead/behind status and manage stale branches."""
    if path:
        ctx.obj["PATH"] = path

    if ctx.invoked_subcommand is None:
        target_path = path or ctx.obj.get("PATH")
        verify_repo_or_exit(target_path)
        try:
            report = analyze_branches(cwd=target_path, include_remotes=include_remotes)
            render_branches(report, console)
        except GitError as e:
            console.print(f"[bold red]Git Error:[/bold red] {e}")
            sys.exit(1)


@branches.command("clean")
@click.option("--dry-run/--yes", default=True, help="Preview branches to delete without modifying.")
@click.option("--path", "-C", type=click.Path(exists=True, file_okay=False, path_type=Path), help="Repository directory.")
@click.pass_context
def branches_clean(ctx: click.Context, dry_run: bool, path: Optional[Path]) -> None:
    """Safely prune local branches already merged into default branch."""
    target_path = path or ctx.obj.get("PATH")
    verify_repo_or_exit(target_path)
    try:
        deleted, errors = prune_merged_branches(cwd=target_path, dry_run=dry_run)
        if dry_run:
            if deleted:
                console.print(f"[yellow]Found {len(deleted)} merged branch(es) eligible for deletion:[/yellow]")
                for b in deleted:
                    console.print(f"  • [red]{b}[/red]")
                console.print("\n[dim]Run [bold]git-pulse branches clean --yes[/bold] to delete them safely.[/dim]")
            else:
                console.print("[green]✔ No stale merged branches found. Clean repository![/green]")
        else:
            if deleted:
                console.print(f"[bold green]✔ Successfully pruned {len(deleted)} merged branch(es):[/bold green]")
                for b in deleted:
                    console.print(f"  • {b}")
            if errors:
                console.print("[bold red]Errors while deleting:[/bold red]")
                for err in errors:
                    console.print(f"  • {err}")
    except GitError as e:
        console.print(f"[bold red]Git Error:[/bold red] {e}")
        sys.exit(1)


@cli.command("changelog")
@click.option("--from", "from_ref", type=str, default=None, help="Starting git revision or tag (defaults to latest tag).")
@click.option("--to", "to_ref", type=str, default="HEAD", show_default=True, help="Target git revision or tag.")
@click.option("--limit", "-n", default=50, show_default=True, type=int, help="Limit number of commits if no tags exist.")
@click.option("--markdown", "-m", is_flag=True, help="Output formatted Markdown directly to stdout.")
@click.option("--output", "-o", type=click.Path(dir_okay=False, path_type=Path), help="Write changelog to a Markdown file.")
@click.option("--path", "-C", type=click.Path(exists=True, file_okay=False, path_type=Path), help="Repository directory.")
def changelog(
    from_ref: Optional[str],
    to_ref: str,
    limit: int,
    markdown: bool,
    output: Optional[Path],
    path: Optional[Path],
) -> None:
    """Generate categorized release notes from Conventional Commits."""
    target_path = path or click.get_current_context().obj.get("PATH")
    verify_repo_or_exit(target_path)
    try:
        report = generate_changelog(cwd=target_path, from_ref=from_ref, to_ref=to_ref, limit=limit)
        md_content = render_markdown_changelog(report)

        if output:
            output.write_text(md_content, encoding="utf-8")
            console.print(f"[bold green]✔ Changelog written to {output}[/bold green]")
        elif markdown:
            click.echo(md_content)
        else:
            render_changelog(report, console)
    except GitError as e:
        console.print(f"[bold red]Git Error:[/bold red] {e}")
        sys.exit(1)


@cli.command("audit")
@click.option("--max-size", default=5.0, show_default=True, type=float, help="File size threshold in MB for bloat warnings.")
@click.option("--path", "-C", type=click.Path(exists=True, file_okay=False, path_type=Path), help="Repository directory.")
def audit(max_size: float, path: Optional[Path]) -> None:
    """Run hygiene, secret leak detection, and health audit on repository."""
    target_path = path or click.get_current_context().obj.get("PATH")
    verify_repo_or_exit(target_path)
    try:
        report = audit_repository(cwd=target_path, max_file_size_mb=max_size)
        render_audit(report, console)
    except GitError as e:
        console.print(f"[bold red]Git Error:[/bold red] {e}")
        sys.exit(1)


def main() -> None:
    """CLI Entrypoint."""
    cli()


if __name__ == "__main__":
    main()
