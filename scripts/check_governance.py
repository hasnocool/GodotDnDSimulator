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
    "docs/V0.6_SPATIAL_AUTHORITY.md",
    "docs/V0.7_GODOT_VERTICAL_SLICE.md",
    "docs/V0.8_SPELL_RUNTIME.md",
    "docs/V0.9_CHARACTER_CREATOR.md",
    "docs/V1.0_PLAYABLE_RPG.md",
    "docs/V1.0_GODOT_SAVE_LOAD.md",
    "docs/V1.0_GODOT_RPG_COMPLETION.md",
    "docs/adr/0001-engine-runtime.md",
    "docs/adr/0002-versioning.md",
    "pyproject.toml",
    "apps/godot-client/AGENTS.md",
    "apps/godot-client/TODO.md",
    "apps/godot-client/CREDITS.md",
    "apps/godot-client/project.godot",
    "schemas/v1/command.schema.json",
    "schemas/v1/event.schema.json",
    "schemas/v1/snapshot.schema.json",
    "schemas/v1/spatial-event.schema.json",
    "schemas/v1/spell-event.schema.json",
    "schemas/v1/character-record.schema.json",
    "schemas/v1/world-event.schema.json",
    "schemas/v1/godot-world-save-envelope.schema.json",
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
    client_agents = _read("apps/godot-client/AGENTS.md")
    client_todo = _read("apps/godot-client/TODO.md")

    milestone_focuses = tuple(
        f"## Current focus: {version} {name}"
        for version, name in (
            ("v0.1", "Project foundation"),
            ("v0.2", "Official SRD pipeline"),
            ("v0.3", "Rules runtime"),
            ("v0.4", "Character runtime"),
            ("v0.5", "Tactical combat"),
            ("v0.6", "Spatial authority"),
            ("v0.7", "Godot vertical slice"),
            ("v0.8", "Spell runtime"),
            ("v0.9", "Complete character creator"),
            ("v1.0", "Playable RPG"),
        )
    )
    if not any(focus in todo for focus in milestone_focuses):
        errors.append(
            "TODO.md must declare a recognized current milestone focus "
            "from v0.1 through v1.0"
        )
    if "## [Unreleased]" not in changelog:
        errors.append("CHANGELOG.md must contain an Unreleased section")
    if "Command -> Validation -> Resolution -> Events -> Reducer -> New State" not in agents:
        errors.append("AGENTS.md no longer contains the canonical simulation flow")
    if "Authoritative Headless Engine" not in architecture:
        errors.append(
            "architecture contract no longer identifies the authoritative headless engine"
        )

    client_requirements = (
        (agents, "apps/godot-client/AGENTS.md", "root AGENTS client contract reference"),
        (agents, "apps/godot-client/TODO.md", "root AGENTS client TODO reference"),
        (client_agents, "presentation", "client presentation-authority boundary"),
        (client_agents, "headless", "client headless-testing requirement"),
        (client_todo, "## C21 — v1.0 RPG client shell", "client v1.0 execution section"),
        (
            client_todo,
            "docs/V1.0_GODOT_RPG_COMPLETION.md",
            "client v1.0 completion evidence",
        ),
    )
    for content, needle, label in client_requirements:
        if needle not in content:
            errors.append(f"missing {label}: {needle}")

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
