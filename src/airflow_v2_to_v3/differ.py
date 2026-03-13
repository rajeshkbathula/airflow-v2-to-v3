"""Side-by-side diff output — like a GitHub PR view in the terminal."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .transformer import TransformResult


@dataclass
class DiffBlock:
    """One contiguous block of changed lines."""

    old_start: int
    old_lines: list[str]
    new_start: int
    new_lines: list[str]


def compute_diff_blocks(original: str, transformed: str) -> list[DiffBlock]:
    """Compute diff blocks between original and transformed source."""
    old_lines = original.splitlines(keepends=True)
    new_lines = transformed.splitlines(keepends=True)
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    blocks: list[DiffBlock] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        blocks.append(DiffBlock(
            old_start=i1 + 1,
            old_lines=[l.rstrip("\n") for l in old_lines[i1:i2]],
            new_start=j1 + 1,
            new_lines=[l.rstrip("\n") for l in new_lines[j1:j2]],
        ))

    return blocks


def format_diff_text(result: TransformResult) -> str:
    """Return a plain-text unified diff."""
    old_lines = result.original.splitlines(keepends=True)
    new_lines = result.transformed.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{result.path}",
        tofile=f"b/{result.path}",
    )
    return "".join(diff)


def print_side_by_side(result: TransformResult, console: Console | None = None) -> None:
    """Print a rich side-by-side diff table (like a GitHub PR)."""
    if not result.changed:
        return

    console = console or Console()
    blocks = compute_diff_blocks(result.original, result.transformed)

    table = Table(
        title=str(result.path),
        show_lines=True,
        title_style="bold cyan",
        border_style="dim",
        pad_edge=False,
    )
    table.add_column("Line", style="dim", width=5, justify="right")
    table.add_column("Original (Airflow 2)", style="red", ratio=1, overflow="fold")
    table.add_column("Line", style="dim", width=5, justify="right")
    table.add_column("Migrated (Airflow 3)", style="green", ratio=1, overflow="fold")

    for block in blocks:
        max_len = max(len(block.old_lines), len(block.new_lines))
        for i in range(max_len):
            old_ln = str(block.old_start + i) if i < len(block.old_lines) else ""
            old_txt = block.old_lines[i] if i < len(block.old_lines) else ""
            new_ln = str(block.new_start + i) if i < len(block.new_lines) else ""
            new_txt = block.new_lines[i] if i < len(block.new_lines) else ""

            old_text = Text(old_txt)
            new_text = Text(new_txt)

            if old_txt and not new_txt:
                old_text.stylize("bold red")
            elif new_txt and not old_txt:
                new_text.stylize("bold green")

            table.add_row(old_ln, old_text, new_ln, new_text)

    console.print(table)


def _format_side_by_side_text(result: TransformResult, col_width: int = 60) -> str:
    """Format a text-based side-by-side diff for a single file."""
    blocks = compute_diff_blocks(result.original, result.transformed)
    lines: list[str] = []
    sep = " │ "
    header_left = "Original (Airflow 2)".center(col_width + 6)
    header_right = "Migrated (Airflow 3)".center(col_width + 6)
    lines.append(f"{header_left}{sep}{header_right}")
    lines.append("─" * (col_width + 6) + "─┼─" + "─" * (col_width + 6))

    for block in blocks:
        max_len = max(len(block.old_lines), len(block.new_lines))
        for i in range(max_len):
            old_ln = str(block.old_start + i) if i < len(block.old_lines) else ""
            old_txt = block.old_lines[i] if i < len(block.old_lines) else ""
            new_ln = str(block.new_start + i) if i < len(block.new_lines) else ""
            new_txt = block.new_lines[i] if i < len(block.new_lines) else ""

            left = f"{old_ln:>5} {old_txt:<{col_width}}"
            right = f"{new_ln:>5} {new_txt:<{col_width}}"
            lines.append(f"{left}{sep}{right}")

    return "\n".join(lines)


def write_diff_report(results: list[TransformResult], output_path: Path) -> None:
    """Write a combined side-by-side diff report to a file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    parts: list[str] = []
    parts.append("=" * 130)
    parts.append("AIRFLOW 2 → 3 MIGRATION DIFF REPORT (SIDE-BY-SIDE)")
    parts.append("=" * 130)
    parts.append("")

    changed_count = sum(1 for r in results if r.changed)
    parts.append(f"Files scanned: {len(results)}")
    parts.append(f"Files changed: {changed_count}")
    parts.append("")

    for result in results:
        if not result.changed:
            continue
        parts.append("─" * 130)
        parts.append(f"File: {result.path}")
        parts.append(f"Changes: {len(result.changes)}")
        parts.append("─" * 130)
        for ch in result.changes:
            parts.append(f"  L{ch.line} [{ch.category}] {ch.message}")
        parts.append("")
        parts.append(_format_side_by_side_text(result))
        parts.append("")

    output_path.write_text("\n".join(parts), encoding="utf-8")
