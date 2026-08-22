#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"
VENV_RUFF="$ROOT_DIR/.venv/bin/ruff"
VENV_MYPY="$ROOT_DIR/.venv/bin/mypy"
VENV_PYTEST="$ROOT_DIR/.venv/bin/pytest"

"$VENV_RUFF" check "$ROOT_DIR"
"$VENV_MYPY" "$ROOT_DIR/engine/src" "$ROOT_DIR/tools/rules_importer"
"$VENV_PYTHON" -m pytest --cov=godot_dnd_engine --cov=tools.rules_importer --cov-report=term-missing
"$VENV_PYTHON" "$ROOT_DIR/scripts/check_governance.py"
"$VENV_PYTHON" "$ROOT_DIR/scripts/determinism_smoke.py"
"$VENV_PYTHON" -m tools.rules_importer.smoke
godot --headless --path "$ROOT_DIR/apps/godot-client" --script res://tests/bridge_tests.gd
godot --headless --path "$ROOT_DIR/apps/godot-client" --script res://tests/authoritative_mirror_tests.gd
godot --headless --path "$ROOT_DIR/apps/godot-client" --script res://tests/state_shell_tests.gd
godot --headless --path "$ROOT_DIR/apps/godot-client" --script res://tests/input_interaction_tests.gd
godot --headless --path "$ROOT_DIR/apps/godot-client" --script res://tests/tactical_camera_tests.gd
godot --headless --path "$ROOT_DIR/apps/godot-client" --script res://tests/tactical_vertical_slice_tests.gd
godot --headless --path "$ROOT_DIR/apps/godot-client" --script res://tests/spell_ui_tests.gd
godot --headless --path "$ROOT_DIR/apps/godot-client" --script res://tests/character_creator_tests.gd
godot --headless --path "$ROOT_DIR/apps/godot-client" --script res://tests/world_rpg_tests.gd
