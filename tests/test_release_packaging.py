from __future__ import annotations

import json
import zipfile
from pathlib import Path

from scripts.package_v1_release import build_release_bundle


def test_v1_release_bundle_is_deterministic_and_attributed(tmp_path: Path) -> None:
    first = build_release_bundle(tmp_path / "first.zip")
    second = build_release_bundle(tmp_path / "second.zip")

    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        names = set(archive.namelist())
        assert "apps/godot-client/project.godot" in names
        assert "apps/godot-client/main.tscn" in names
        assert "apps/godot-client/CREDITS.md" in names
        assert "LICENSES/SRD-5.2.1-ATTRIBUTION.txt" in names
        assert "README.md" in names
        assert "RELEASE-MANIFEST.json" in names

        manifest = json.loads(archive.read("RELEASE-MANIFEST.json"))
        assert manifest["format"] == "godot-dnd-v1-release-bundle"
        assert manifest["format_version"] == 1
        assert manifest["engine_binary_included"] is False
        manifest_paths = {row["path"] for row in manifest["files"]}
        assert "apps/godot-client/CREDITS.md" in manifest_paths
        assert "LICENSES/SRD-5.2.1-ATTRIBUTION.txt" in manifest_paths
