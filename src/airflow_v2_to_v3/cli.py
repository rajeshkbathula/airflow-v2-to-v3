"""CLI entry point for airflow-v2-to-v3."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .differ import print_side_by_side, write_diff_report
from .transformer import TransformResult, transform_file, transform_source
from .validator import Severity, validate_directory, validate_file

console = Console()


@click.group()
@click.version_option()
def main() -> None:
    """Airflow 2 → 3 migration tool for Astro / Apache Airflow DAGs.

    Validate, transform, and diff your DAGs.
    """


# ── validate ────────────────────────────────────────────────────────────────


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("--format", "fmt", type=click.Choice(["table", "json", "text"]), default="table")
def validate(path: str, fmt: str) -> None:
    """Validate DAG files for Airflow 3 compatibility.

    PATH can be a single .py file or a directory.
    """
    p = Path(path)
    if p.is_file():
        result = validate_file(p)
    else:
        result = validate_directory(p)

    if fmt == "json":
        import json
        issues = [
            {
                "file": i.file,
                "line": i.line,
                "severity": i.severity.value,
                "code": i.code,
                "message": i.message,
            }
            for i in result.issues
        ]
        click.echo(json.dumps(issues, indent=2))
        sys.exit(0 if result.passed else 1)

    if fmt == "text":
        for i in result.issues:
            click.echo(f"{i.file}:{i.line}: {i.severity.value.upper()} [{i.code}] {i.message}")
        _print_summary(result)
        sys.exit(0 if result.passed else 1)

    # table (default)
    if not result.issues:
        console.print("[bold green]All clear![/] No Airflow 3 compatibility issues found.")
        sys.exit(0)

    table = Table(title="Airflow 3 Compatibility Issues", show_lines=True)
    table.add_column("File", style="cyan")
    table.add_column("Line", style="dim", justify="right")
    table.add_column("Severity", justify="center")
    table.add_column("Code", style="yellow")
    table.add_column("Message")

    severity_style = {
        Severity.ERROR: "bold red",
        Severity.WARNING: "yellow",
        Severity.INFO: "dim",
    }

    for i in result.issues:
        table.add_row(
            i.file,
            str(i.line),
            f"[{severity_style[i.severity]}]{i.severity.value.upper()}[/]",
            i.code,
            i.message,
        )

    console.print(table)
    _print_summary(result)
    sys.exit(0 if result.passed else 1)


def _print_summary(result) -> None:
    console.print(
        f"\n[bold]Summary:[/] "
        f"[red]{result.error_count} errors[/], "
        f"[yellow]{result.warning_count} warnings[/], "
        f"[dim]{result.info_count} info[/]"
    )
    if result.passed:
        console.print("[bold green]Validation passed (no errors).[/]")
    else:
        console.print("[bold red]Validation failed.[/]")


# ── migrate ─────────────────────────────────────────────────────────────────


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option("-o", "--output", "output_dir", type=click.Path(), default=None,
              help="Write migrated files to this directory (preserves originals).")
@click.option("--diff/--no-diff", default=True, help="Show side-by-side diff.")
@click.option("--diff-report", type=click.Path(), default=None,
              help="Write a diff report file.")
@click.option("--dry-run", is_flag=True, help="Show what would change without writing files.")
def migrate(path: str, output_dir: str | None, diff: bool, diff_report: str | None, dry_run: bool) -> None:
    """Migrate DAG files from Airflow 2 → 3.

    PATH can be a single .py file or a directory.
    """
    p = Path(path)
    out = Path(output_dir) if output_dir else None
    results: list[TransformResult] = []

    files = _collect_py_files(p)
    if not files:
        console.print("[yellow]No Python files found.[/]")
        sys.exit(0)

    for fpath in files:
        if dry_run or out:
            source = fpath.read_text(encoding="utf-8")
            result = transform_source(source, filename=str(fpath))
            result.path = fpath
            if out and result.changed and not dry_run:
                # Preserve relative structure
                rel = fpath.relative_to(p) if p.is_dir() else fpath.name
                dest = out / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(result.transformed, encoding="utf-8")
                result.path = dest
        else:
            result = transform_file(fpath)

        results.append(result)

    changed = [r for r in results if r.changed]
    unchanged = len(results) - len(changed)

    if not changed:
        console.print("[bold green]No changes needed — DAGs are already Airflow 3 compatible.[/]")
        sys.exit(0)

    # Show diffs
    if diff:
        for r in changed:
            print_side_by_side(r, console)
            console.print()
            # Print change summary under each file
            for ch in r.changes:
                console.print(f"  [dim]L{ch.line}[/] [{ch.category}] {ch.message}")
            console.print()

    # Write diff report
    if diff_report:
        write_diff_report(results, Path(diff_report))
        console.print(f"[cyan]Diff report written to:[/] {diff_report}")

    # Summary
    action = "Would migrate" if dry_run else "Migrated"
    console.print(
        f"\n[bold]{action}:[/] "
        f"[green]{len(changed)} file(s) changed[/], "
        f"[dim]{unchanged} file(s) unchanged[/]"
    )
    total_changes = sum(len(r.changes) for r in changed)
    console.print(f"[bold]Total transformations:[/] {total_changes}")

    if out and not dry_run:
        console.print(f"[cyan]Output directory:[/] {out}")


# ── diff ────────────────────────────────────────────────────────────────────


@main.command(name="diff")
@click.argument("path", type=click.Path(exists=True))
@click.option("-o", "--output", "report_file", type=click.Path(), default=None,
              help="Write diff report to file.")
def diff_cmd(path: str, report_file: str | None) -> None:
    """Show what would change without modifying any files.

    Like 'migrate --dry-run' but focused on the diff output.
    """
    p = Path(path)
    files = _collect_py_files(p)
    results: list[TransformResult] = []

    for fpath in files:
        source = fpath.read_text(encoding="utf-8")
        result = transform_source(source, filename=str(fpath))
        result.path = fpath
        results.append(result)

    changed = [r for r in results if r.changed]

    if not changed:
        console.print("[bold green]No changes needed.[/]")
        sys.exit(0)

    for r in changed:
        print_side_by_side(r, console)
        console.print()

    if report_file:
        write_diff_report(results, Path(report_file))
        console.print(f"[cyan]Report written to:[/] {report_file}")


# ── helpers ─────────────────────────────────────────────────────────────────


def _collect_py_files(p: Path) -> list[Path]:
    if p.is_file() and p.suffix == ".py":
        return [p]
    if p.is_dir():
        return sorted(p.rglob("*.py"))
    return []
