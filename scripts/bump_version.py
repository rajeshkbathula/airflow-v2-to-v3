#!/usr/bin/env python3
"""Bump version in pyproject.toml and __init__.py following semver."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
INIT = ROOT / "src" / "airflow_v2_to_v3" / "__init__.py"


def get_version() -> str:
    text = PYPROJECT.read_text()
    match = re.search(r'version\s*=\s*"(.+?)"', text)
    if not match:
        raise RuntimeError("Could not find version in pyproject.toml")
    return match.group(1)


def bump(version: str, part: str) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    if part == "patch":
        patch += 1
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "major":
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError(f"Unknown part: {part}")
    return f"{major}.{minor}.{patch}"


def set_version(new_version: str) -> None:
    for fpath in (PYPROJECT, INIT):
        text = fpath.read_text()
        text = re.sub(
            r'(version\s*=\s*")(.+?)(")',
            rf"\g<1>{new_version}\g<3>",
            text,
        )
        text = re.sub(
            r'(__version__\s*=\s*")(.+?)(")',
            rf"\g<1>{new_version}\g<3>",
            text,
        )
        fpath.write_text(text)


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("patch", "minor", "major"):
        print("Usage: bump_version.py [patch|minor|major]")
        sys.exit(1)

    part = sys.argv[1]
    old = get_version()
    new = bump(old, part)
    set_version(new)
    print(f"{old} → {new}")


if __name__ == "__main__":
    main()
