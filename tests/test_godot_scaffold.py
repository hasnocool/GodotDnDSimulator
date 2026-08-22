# tests/test_godot_scaffold.py
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GODOT_ROOT = ROOT / "apps" / "godot-client"
RESOURCE_PATTERN = re.compile(r'res://([^"\s]+)')


def _resource_paths(text: str) -> set[str]:
    return set(RESOURCE_PATTERN.findall(text))


def test_project_main_scene_and_scene_resources_exist() -> None:
    project_text = (GODOT_ROOT / "project.godot").read_text(encoding="utf-8")
    main_scene_text = (GODOT_ROOT / "main.tscn").read_text(encoding="utf-8")
    shell_scene_text = (GODOT_ROOT / "scenes/shell/app_shell.tscn").read_text(
        encoding="utf-8"
    )
    tactical_scene_text = (GODOT_ROOT / "scenes/tactical/tactical_stub.tscn").read_text(
        encoding="utf-8"
    )

    referenced = (
        _resource_paths(project_text)
        | _resource_paths(main_scene_text)
        | _resource_paths(shell_scene_text)
        | _resource_paths(tactical_scene_text)
    )
    assert "scenes/shell/app_shell.tscn" in referenced
    assert "scenes/shell/app_shell.gd" in referenced
    assert "autoload/client_log.gd" in referenced
    assert "autoload/client_settings.gd" in referenced
    assert "debug/client_debug_overlay.tscn" in referenced

    # Tactical scene is loaded dynamically at runtime via tactical_scene_path in app_shell.gd
    assert (GODOT_ROOT / "scenes/tactical/tactical_stub.tscn").is_file()
    assert (GODOT_ROOT / "scenes/tactical/tactical_stub.gd").is_file()

    missing = sorted(path for path in referenced if not (GODOT_ROOT / path).is_file())
    assert not missing, f"missing Godot res:// references: {missing}"


def test_main_scene_keeps_orthographic_presentation_boundary() -> None:
    scene_text = (GODOT_ROOT / "scenes/tactical/tactical_stub.tscn").read_text(encoding="utf-8")
    shell_text = (GODOT_ROOT / "scenes/shell/app_shell.gd").read_text(encoding="utf-8")

    assert '[node name="Camera3D" type="Camera3D" parent="CameraRig"]' in scene_text
    assert "projection = 1" in scene_text
    assert "current = true" in scene_text
    assert "authoritative" in shell_text.lower()