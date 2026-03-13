"""AST-based transformer that rewrites Airflow 2 DAG files to Airflow 3."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import rules


@dataclass
class Change:
    """A single migration change applied to a file."""

    line: int
    category: str  # e.g. "import", "param", "class", "context_var", "reserved_kw"
    old: str
    new: str
    message: str


@dataclass
class TransformResult:
    """Result of transforming a single file."""

    path: Path
    original: str
    transformed: str
    changes: list[Change] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.original != self.transformed


def transform_source(source: str, filename: str = "<unknown>") -> TransformResult:
    """Transform a single source string from Airflow 2 → 3.

    Returns a TransformResult with the rewritten source and a list of changes.
    """
    changes: list[Change] = []
    lines = source.splitlines(keepends=True)

    # --- Pass 1: import rewrites ------------------------------------------
    lines, import_changes = _rewrite_imports(lines)

    # --- Pass 2: parameter renames & removals -----------------------------
    lines, param_changes = _rewrite_params(lines)

    # --- Pass 3: class renames (DummyOperator → EmptyOperator, etc.) ------
    lines, class_changes = _rewrite_classes(lines)

    # --- Pass 4: context variable replacements ----------------------------
    lines, ctx_changes = _rewrite_context_vars(lines)

    # --- Pass 5: days_ago → pendulum -------------------------------------
    lines, days_ago_changes = _rewrite_days_ago(lines)

    # --- Pass 6: apply_defaults removal -----------------------------------
    lines, ad_changes = _rewrite_apply_defaults(lines)

    # --- Pass 7: trigger rule renames ------------------------------------
    lines, tr_changes = _rewrite_trigger_rules(lines)

    # --- Pass 8: method renames (dataset → asset) ------------------------
    lines, method_changes = _rewrite_methods(lines)

    changes = (
        import_changes
        + param_changes
        + class_changes
        + ctx_changes
        + days_ago_changes
        + ad_changes
        + tr_changes
        + method_changes
    )

    transformed = "".join(lines)
    return TransformResult(
        path=Path(filename),
        original=source,
        transformed=transformed,
        changes=changes,
    )


def transform_file(path: Path, output_path: Path | None = None) -> TransformResult:
    """Transform a DAG file in-place or write to *output_path*."""
    source = path.read_text(encoding="utf-8")
    result = transform_source(source, filename=str(path))

    if result.changed:
        dest = output_path or path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(result.transformed, encoding="utf-8")
        result.path = dest

    return result


# ── internal helpers ────────────────────────────────────────────────────────


def _rewrite_imports(lines: list[str]) -> tuple[list[str], list[Change]]:
    """Rewrite import statements based on IMPORT_MOVES.

    Handles both:
      - ``import airflow.operators.bash_operator``  (direct module match)
      - ``from airflow.models import DAG``  (module.name split across from/import)
    """
    changes: list[Change] = []
    new_lines: list[str] = []

    for lineno, line in enumerate(lines, start=1):
        original = line
        if "import" not in line:
            new_lines.append(line)
            continue

        matched = False

        for old_mod, new_mod in rules.IMPORT_MOVES.items():
            # Case 1: the full dotted path appears literally in the line
            if old_mod in line:
                if not new_mod:
                    changes.append(
                        Change(lineno, "import", old_mod, "(removed)", f"Removed import: {old_mod}")
                    )
                    line = f"# REMOVED (Airflow 3): {original.rstrip()}\n"
                else:
                    line = line.replace(old_mod, new_mod)
                    changes.append(
                        Change(lineno, "import", old_mod, new_mod, f"Moved: {old_mod} → {new_mod}")
                    )
                matched = True
                break

            # Case 2: ``from <parent> import <name>`` where old_mod == parent.name
            if "." in old_mod:
                parent, name = old_mod.rsplit(".", 1)
                # Match: from <parent> import <...name...>
                from_pat = re.compile(
                    rf'^(\s*from\s+){re.escape(parent)}(\s+import\s+.*\b){re.escape(name)}(\b.*)'
                )
                m = from_pat.match(line)
                if m:
                    if not new_mod:
                        changes.append(
                            Change(lineno, "import", old_mod, "(removed)", f"Removed import: {old_mod}")
                        )
                        line = f"# REMOVED (Airflow 3): {original.rstrip()}\n"
                    else:
                        # new_mod is the target module to import from.
                        # e.g. old_mod="airflow.models.Variable" new_mod="airflow.sdk"
                        # means: from airflow.models import Variable → from airflow.sdk import Variable
                        line = line.replace(parent, new_mod, 1)
                        changes.append(
                            Change(lineno, "import", old_mod, f"{new_mod}.{name}", f"Moved: {old_mod} → {new_mod}")
                        )
                    matched = True
                    break

        new_lines.append(line)

    return new_lines, changes


def _rewrite_params(lines: list[str]) -> tuple[list[str], list[Change]]:
    """Rename / remove deprecated keyword arguments."""
    changes: list[Change] = []
    new_lines: list[str] = []

    for lineno, line in enumerate(lines, start=1):
        original = line

        # Renames
        for old_p, new_p in rules.PARAM_RENAMES.items():
            pattern = rf'\b{re.escape(old_p)}\s*='
            if re.search(pattern, line):
                line = re.sub(rf'\b{re.escape(old_p)}(\s*=)', rf'{new_p}\1', line)
                changes.append(
                    Change(lineno, "param", old_p, new_p, f"Renamed parameter: {old_p} → {new_p}")
                )

        # Removals — remove the entire kwarg (handles trailing comma)
        for old_p, reason in rules.PARAMS_REMOVED.items():
            pattern = rf',?\s*{re.escape(old_p)}\s*=\s*[^,\)]*,?'
            if re.search(rf'\b{re.escape(old_p)}\s*=', line):
                line = re.sub(pattern, '', line)
                # Clean up double commas / leading commas
                line = re.sub(r',\s*,', ',', line)
                line = re.sub(r'\(\s*,', '(', line)
                changes.append(
                    Change(lineno, "param", old_p, "(removed)", f"Removed parameter: {old_p} — {reason}")
                )

        new_lines.append(line)

    return new_lines, changes


def _rewrite_classes(lines: list[str]) -> tuple[list[str], list[Change]]:
    """Rename deprecated classes."""
    changes: list[Change] = []
    new_lines: list[str] = []

    for lineno, line in enumerate(lines, start=1):
        for old_cls, new_cls in rules.CLASS_RENAMES.items():
            if old_cls in line:
                line = line.replace(old_cls, new_cls)
                changes.append(
                    Change(lineno, "class", old_cls, new_cls, f"Renamed class: {old_cls} → {new_cls}")
                )

        new_lines.append(line)

    return new_lines, changes


def _rewrite_context_vars(lines: list[str]) -> tuple[list[str], list[Change]]:
    """Flag/replace removed context variables."""
    changes: list[Change] = []
    new_lines: list[str] = []

    for lineno, line in enumerate(lines, start=1):
        for old_var, new_var in rules.REMOVED_CONTEXT_VARS.items():
            # Match context dict access patterns like context['execution_date'] or kwargs['execution_date']
            patterns = [
                rf"""(\[['"]){re.escape(old_var)}(['"]\])""",
                rf"""(\.get\(\s*['"]){re.escape(old_var)}(['"]\s*\))""",
            ]
            for pat in patterns:
                if re.search(pat, line):
                    if new_var:
                        line = re.sub(pat, rf'\g<1>{new_var}\g<2>', line)
                        changes.append(
                            Change(
                                lineno, "context_var", old_var, new_var,
                                f"Replaced context variable: {old_var} → {new_var}"
                            )
                        )
                    else:
                        line = line.rstrip() + f"  # TODO(airflow3): '{old_var}' removed, no direct replacement\n"
                        changes.append(
                            Change(
                                lineno, "context_var", old_var, "(removed)",
                                f"Removed context variable: {old_var} — no direct replacement"
                            )
                        )

        new_lines.append(line)

    return new_lines, changes


def _rewrite_days_ago(lines: list[str]) -> tuple[list[str], list[Change]]:
    """Replace days_ago(N) with pendulum equivalent."""
    changes: list[Change] = []
    new_lines: list[str] = []

    for lineno, line in enumerate(lines, start=1):
        match = re.search(r'\bdays_ago\(\s*(\d+)\s*\)', line)
        if match:
            n = match.group(1)
            replacement = f"pendulum.today('UTC').add(days=-{n})"
            line = line.replace(match.group(0), replacement)
            changes.append(
                Change(lineno, "function", f"days_ago({n})", replacement, f"Replaced days_ago({n}) with pendulum")
            )
            # Add pendulum import if not already present
            # (handled later — we just flag it)

        new_lines.append(line)

    return new_lines, changes


def _rewrite_apply_defaults(lines: list[str]) -> tuple[list[str], list[Change]]:
    """Remove @apply_defaults decorator lines."""
    changes: list[Change] = []
    new_lines: list[str] = []

    for lineno, line in enumerate(lines, start=1):
        if re.search(r'@\s*apply_defaults\b', line):
            changes.append(
                Change(lineno, "decorator", "@apply_defaults", "(removed)", "Removed @apply_defaults — it is now unconditional")
            )
            continue  # skip line entirely

        new_lines.append(line)

    return new_lines, changes


def _rewrite_trigger_rules(lines: list[str]) -> tuple[list[str], list[Change]]:
    """Rename deprecated trigger rule values."""
    changes: list[Change] = []
    new_lines: list[str] = []

    for lineno, line in enumerate(lines, start=1):
        for old_rule, new_rule in rules.TRIGGER_RULE_RENAMES.items():
            patterns = [
                rf"""(trigger_rule\s*=\s*['"]){re.escape(old_rule)}(['"])""",
                rf"""(TriggerRule\.){old_rule.upper()}""",
            ]
            for pat in patterns:
                if re.search(pat, line):
                    if "TriggerRule." in line:
                        line = re.sub(pat, rf'\g<1>{new_rule.upper()}', line)
                    else:
                        line = re.sub(pat, rf'\g<1>{new_rule}\g<2>', line)
                    changes.append(
                        Change(lineno, "trigger_rule", old_rule, new_rule, f"Renamed trigger rule: {old_rule} → {new_rule}")
                    )

        new_lines.append(line)

    return new_lines, changes


def _rewrite_methods(lines: list[str]) -> tuple[list[str], list[Change]]:
    """Rename dataset → asset methods/attributes."""
    changes: list[Change] = []
    new_lines: list[str] = []

    for lineno, line in enumerate(lines, start=1):
        for old_m, new_m in rules.METHOD_RENAMES.items():
            if old_m in line:
                line = line.replace(old_m, new_m)
                changes.append(
                    Change(lineno, "method", old_m, new_m, f"Renamed method: {old_m} → {new_m}")
                )

        new_lines.append(line)

    return new_lines, changes
