"""Validate Airflow DAG files for Airflow 3 compatibility.

Scans for issues without modifying files.  Returns structured diagnostics.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from . import rules


class Severity(str, Enum):
    ERROR = "error"       # Will break in Airflow 3
    WARNING = "warning"   # Deprecated / will be removed soon
    INFO = "info"         # Suggested improvement


@dataclass
class Issue:
    file: str
    line: int
    severity: Severity
    code: str        # e.g. "AIR301", "AIR302", "RESERVED_KW"
    message: str


@dataclass
class ValidationResult:
    issues: list[Issue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.INFO)


def validate_source(source: str, filename: str = "<unknown>") -> ValidationResult:
    """Validate a source string for Airflow 3 compatibility issues."""
    result = ValidationResult()
    lines = source.splitlines()

    for lineno, line in enumerate(lines, start=1):
        _check_imports(line, lineno, filename, result)
        _check_params(line, lineno, filename, result)
        _check_context_vars(line, lineno, filename, result)
        _check_removed_functions(line, lineno, filename, result)
        _check_class_renames(line, lineno, filename, result)
        _check_trigger_rules(line, lineno, filename, result)

    return result


def validate_file(path: Path) -> ValidationResult:
    """Validate a single file."""
    source = path.read_text(encoding="utf-8")
    return validate_source(source, filename=str(path))


def validate_directory(directory: Path) -> ValidationResult:
    """Validate all Python files in a directory (recursively)."""
    result = ValidationResult()
    for root, _dirs, files in os.walk(directory):
        for fname in files:
            if fname.endswith(".py"):
                fpath = Path(root) / fname
                file_result = validate_file(fpath)
                result.issues.extend(file_result.issues)

    # Check for reserved keyword directory names at the root level
    _check_reserved_keywords(directory, result)

    return result


# ── checkers ────────────────────────────────────────────────────────────────


def _check_imports(line: str, lineno: int, filename: str, result: ValidationResult) -> None:
    if "import" not in line:
        return
    for old_mod, new_mod in rules.IMPORT_MOVES.items():
        matched = False
        if old_mod in line:
            matched = True
        elif "." in old_mod:
            # Handle ``from <parent> import <name>`` where old_mod = parent.name
            parent, name = old_mod.rsplit(".", 1)
            if parent in line and re.search(rf'\bimport\b.*\b{re.escape(name)}\b', line):
                matched = True

        if matched:
            if new_mod:
                result.issues.append(Issue(
                    file=filename, line=lineno, severity=Severity.ERROR,
                    code="AIR302",
                    message=f"Import '{old_mod}' moved to '{new_mod}' in Airflow 3",
                ))
            else:
                result.issues.append(Issue(
                    file=filename, line=lineno, severity=Severity.ERROR,
                    code="AIR301",
                    message=f"Import '{old_mod}' removed in Airflow 3",
                ))


def _check_params(line: str, lineno: int, filename: str, result: ValidationResult) -> None:
    for old_p, new_p in rules.PARAM_RENAMES.items():
        if re.search(rf'\b{re.escape(old_p)}\s*=', line):
            result.issues.append(Issue(
                file=filename, line=lineno, severity=Severity.ERROR,
                code="AIR311",
                message=f"Parameter '{old_p}' renamed to '{new_p}' in Airflow 3",
            ))

    for old_p, reason in rules.PARAMS_REMOVED.items():
        if re.search(rf'\b{re.escape(old_p)}\s*=', line):
            result.issues.append(Issue(
                file=filename, line=lineno, severity=Severity.ERROR,
                code="AIR301",
                message=f"Parameter '{old_p}' removed in Airflow 3: {reason}",
            ))


def _check_context_vars(line: str, lineno: int, filename: str, result: ValidationResult) -> None:
    for old_var, new_var in rules.REMOVED_CONTEXT_VARS.items():
        patterns = [
            rf"""(\[['"]){re.escape(old_var)}(['"]\])""",
            rf"""(\.get\(\s*['"]){re.escape(old_var)}(['"]\s*\))""",
        ]
        for pat in patterns:
            if re.search(pat, line):
                if new_var:
                    result.issues.append(Issue(
                        file=filename, line=lineno, severity=Severity.ERROR,
                        code="AIR301",
                        message=f"Context variable '{old_var}' removed — use '{new_var}' instead",
                    ))
                else:
                    result.issues.append(Issue(
                        file=filename, line=lineno, severity=Severity.ERROR,
                        code="AIR301",
                        message=f"Context variable '{old_var}' removed with no direct replacement",
                    ))


def _check_removed_functions(line: str, lineno: int, filename: str, result: ValidationResult) -> None:
    for func, replacement in rules.REMOVED_FUNCTIONS.items():
        if re.search(rf'\b{re.escape(func)}\s*\(', line):
            msg = f"Function '{func}' removed in Airflow 3"
            if replacement:
                msg += f" — use {replacement}"
            result.issues.append(Issue(
                file=filename, line=lineno, severity=Severity.ERROR,
                code="AIR301",
                message=msg,
            ))


def _check_class_renames(line: str, lineno: int, filename: str, result: ValidationResult) -> None:
    for old_cls, new_cls in rules.CLASS_RENAMES.items():
        if re.search(rf'\b{re.escape(old_cls)}\b', line):
            result.issues.append(Issue(
                file=filename, line=lineno, severity=Severity.WARNING,
                code="AIR302",
                message=f"Class '{old_cls}' renamed to '{new_cls}' in Airflow 3",
            ))


def _check_trigger_rules(line: str, lineno: int, filename: str, result: ValidationResult) -> None:
    for old_rule, new_rule in rules.TRIGGER_RULE_RENAMES.items():
        if re.search(rf"""trigger_rule\s*=\s*['"]?{re.escape(old_rule)}""", line) or \
           re.search(rf"""TriggerRule\.{old_rule.upper()}""", line):
            result.issues.append(Issue(
                file=filename, line=lineno, severity=Severity.ERROR,
                code="AIR301",
                message=f"TriggerRule '{old_rule}' renamed to '{new_rule}' in Airflow 3",
            ))


def _check_reserved_keywords(directory: Path, result: ValidationResult) -> None:
    """Check for directories at the root that shadow core Airflow modules."""
    for item in directory.iterdir():
        if item.is_dir() and item.name in rules.RESERVED_KEYWORDS:
            result.issues.append(Issue(
                file=str(item),
                line=0,
                severity=Severity.ERROR,
                code="RESERVED_KW",
                message=rules.RESERVED_KEYWORDS[item.name],
            ))
