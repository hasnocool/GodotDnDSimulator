# scripts/package_v1_release.py
"""Build a deterministic v1 Godot client source release bundle.

The bundle deliberately contains project resources rather than a Godot engine binary. Binary
exports can be wrapped by downstream release automation after the appropriate Godot engine license
notice is supplied. This script guarantees that repository attribution/credits accompany the v1
client resources.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
CLIENT_ROOT = ROOT / "apps" / "godot-client"
LICENSE_ROOT = ROOT / "LICENSES"
DEFAULT_OUTPUT = ROOT / "dist" / "GodotDnDSimulator-v1-client.zip"
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)

EXCLUDED_PARTS = {
    ".godot",
    "__pycache__",
    ".pytest_cache",
}
EXCLUDED_SUFFIXES = {
    ".tmp",
    ".bak",
    ".pyc",
}
REQUIRED_CLIENT_FILES = {
    "apps/godot-client/project.godot",
    "apps/godot-client/main.tscn",
    "apps/godot-client/CREDITS.md",
}
REQUIRED_ROOT_FILES = {
    "README.md",
}


def _should_include(path: Path) -> bool:
    relative_parts = path.relative_to(ROOT).parts
    if any(part in EXCLUDED_PARTS for part in relative_parts):
        return False
    return path.is_file() and path.suffix not in EXCLUDED_SUFFIXES


def release_files() -> list[Path]:
    files = [path for path in CLIENT_ROOT.rglob("*") if _should_include(path)]
    files.extend(
        path for path in LICENSE_ROOT.rglob("*") if _should_include(path)
    )
    files.extend(ROOT / name for name in REQUIRED_ROOT_FILES)
    unique = {path.resolve(): path for path in files if path.is_file()}
    return sorted(
        unique.values(),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def _manifest_rows(files: list[Path]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in files:
        payload = path.read_bytes()
        rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    return rows


def validate_release_inputs(files: list[Path]) -> None:
    relative = {path.relative_to(ROOT).as_posix() for path in files}
    missing = (REQUIRED_CLIENT_FILES | REQUIRED_ROOT_FILES) - relative
    if missing:
        raise ValueError(
            f"release bundle is missing required files: {sorted(missing)!r}"
        )
    attributions = sorted(path for path in relative if path.startswith("LICENSES/"))
    if not attributions:
        raise ValueError(
            "release bundle must contain at least one LICENSES/ attribution file"
        )


def build_release_bundle(output: Path = DEFAULT_OUTPUT) -> Path:
    files = release_files()
    validate_release_inputs(files)
    manifest = {
        "format": "godot-dnd-v1-release-bundle",
        "format_version": 1,
        "client": "GodotDnDSimulator",
        "engine_binary_included": False,
        "files": _manifest_rows(files),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(relative, date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
        manifest_bytes = (
            json.dumps(
                manifest,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            + "\n"
        ).encode("utf-8")
        info = zipfile.ZipInfo(
            "RELEASE-MANIFEST.json",
            date_time=FIXED_ZIP_TIME,
        )
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, manifest_bytes)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build the deterministic GodotDnDSimulator v1 client source release bundle"
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Destination .zip path",
    )
    args = parser.parse_args()
    output = build_release_bundle(args.output.resolve())
    display = output.relative_to(ROOT) if output.is_relative_to(ROOT) else output
    print(PurePosixPath(display))


if __name__ == "__main__":
    main()
