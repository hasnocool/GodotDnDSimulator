# Contributing

`AGENTS.md` is the canonical engineering contract for both humans and coding agents. This guide summarizes the normal contribution path; `docs/GIT_WORKFLOW.md` contains the detailed policy.

## Before changing code

1. Read `README.md`, `AGENTS.md`, `ROADMAP.md`, `TODO.md`, and `CHANGELOG.md`.
2. Identify the active milestone and TODO item your work satisfies.
3. Inspect the owning subsystem and its tests.
4. Create a focused branch from current `main`.

## Architecture constraints

- The Python 3.12 headless engine owns authoritative simulation state.
- Godot is a presentation/input client and must not directly decide rules outcomes.
- State changes follow `Command -> Validation -> Resolution -> Events -> Reducer -> New State`.
- All randomness uses the versioned deterministic RNG/dice service.
- Durable serialized contracts are versioned and require compatibility review when changed.
- Imported rules/content must follow `docs/RULES_INGESTION.md`.

## Local validation

Create a Python 3.12 virtual environment and run:

```bash
python -m pip install -e '.[dev]'
ruff check .
mypy engine/src
pytest --cov=godot_dnd_engine --cov-report=term-missing
python scripts/check_governance.py
python scripts/determinism_smoke.py
```

If Godot 4.7.1 is installed:

```bash
godot --headless --path apps/godot-client --editor --quit
```

## Pull requests

Use a focused branch and Conventional Commit-style messages. Update tests, `TODO.md`, `CHANGELOG.md`, and durable documentation in the same PR whenever they are affected. Fill out `.github/pull_request_template.md` with exact validation commands and results.

Do not merge known failures, weaken tests to get green CI, or hand-edit generated rules data.
