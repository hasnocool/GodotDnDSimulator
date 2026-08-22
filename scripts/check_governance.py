# scripts/check_governance.py
"""Lightweight repository-governance checks used by CI."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "AGENTS.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "README.md",
    "ROADMAP.md",
    "TODO.md",
    "docs/ARCHITECTURE.md",
    "docs/GIT_WORKFLOW.md",
    "docs/PROJECT_PLAN.md",
    "docs/RULES_INGESTION.md",
    "docs/adr/0001-engine-runtime.md",
    "docs/adr/0002-versioning.md",
    "pyproject.toml",
    "apps/godot-client/project.godot",
    "schemas/v1/command.schema.json",
    "schemas/v1/event.schema.json",
    "schemas/v1/snapshot.schema.json",
)


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def run() -> list[str]:
    errors: list[str] = []
    for relative_path in REQUIRED_FILES:
        if not (ROOT / relative_path).is_file():
            errors.append(f"missing required file: {relative_path}")

    if errors:
        return errors

    todo = _read("TODO.md")
    changelog = _read("CHANGELOG.md")
    agents = _read("AGENTS.md")
    architecture = _read("docs/ARCHITECTURE.md")

    if "## Current focus: v0.1 Project foundation" not in todo:
        errors.append("TODO.md must declare the current v0.1 focus until the milestone exits")
    if "## [Unreleased]" not in changelog:
        errors.append("CHANGELOG.md must contain an Unreleased section")
    if "Command -> Validation -> Resolution -> Events -> Reducer -> New State" not in agents:
        errors.append("AGENTS.md no longer contains the canonical simulation flow")
    if "Authoritative Headless Engine" not in architecture:
        errors.append(
            "architecture contract no longer identifies the authoritative headless engine"
        )

    for path in sorted((ROOT / "engine").rglob("*.py")):
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
        expected = f"# {path.relative_to(ROOT).as_posix()}"
        if first_line != expected:
            errors.append(
                f"{path.relative_to(ROOT)} must start with filename comment {expected!r}"
            )

    for path in sorted((ROOT / "scripts").glob("*.py")):
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
        expected = f"# {path.relative_to(ROOT).as_posix()}"
        if first_line != expected:
            errors.append(
                f"{path.relative_to(ROOT)} must start with filename comment {expected!r}"
            )

    return errors


def main() -> int:
    errors = run()
    if errors:
        print("Governance checks failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Governance checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
