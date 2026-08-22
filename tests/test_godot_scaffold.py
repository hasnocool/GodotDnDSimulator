# tests/test_godot_scaffold.py
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
GODOT_ROOT = ROOT / "apps" / "godot-client"
RESOURCE_PATTERN = re.compile(r'res://([^"\s]+)')


def _resource_paths(text: str) -> set[str]:
    return set(RESOURCE_PATTERN.findall(text))


def test_project_main_scene_and_scene_resources_exist() -> None:
    project_text = (GODOT_ROOT / "project.godot").read_text(encoding="utf-8")
    scene_text = (GODOT_ROOT / "main.tscn").read_text(encoding="utf-8")

    referenced = _resource_paths(project_text) | _resource_paths(scene_text)
    assert "main.tscn" in referenced
    assert "scripts/main.gd" in referenced

    missing = sorted(path for path in referenced if not (GODOT_ROOT / path).is_file())
    assert not missing, f"missing Godot res:// references: {missing}"


def test_main_scene_keeps_orthographic_presentation_boundary() -> None:
    scene_text = (GODOT_ROOT / "main.tscn").read_text(encoding="utf-8")
    script_text = (GODOT_ROOT / "scripts" / "main.gd").read_text(encoding="utf-8")

    assert '[node name="Camera3D" type="Camera3D" parent="CameraRig"]' in scene_text
    assert "projection = 1" in scene_text
    assert "current = true" in scene_text
    assert script_text.startswith("# apps/godot-client/scripts/main.gd\nextends Node3D\n")
    assert "authoritative" in script_text.lower()
