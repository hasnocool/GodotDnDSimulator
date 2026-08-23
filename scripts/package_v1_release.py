# scripts/package_v1_release.py
"""Build a deterministic v1 Godot client source release bundle.

The bundle deliberately contains project resources rather than a Godot engine binary. Binary
exports can be wrapped by downstream release automation after the appropriate Godot engine license
notice is supplied. This script guarantees that repository attribution/credits accompany the v1
client resources and only packages tracked, explicitly allowed repository files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "dist" / "GodotDnDSimulator-v1-client.zip"
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)

TRACKED_ROOTS = (
    "apps/godot-client",
    "LICENSES",
    "README.md",
)
EXCLUDED_PREFIXES = (
    "apps/godot-client/addons/godot-mcp/",
)
EXCLUDED_PARTS = {
    ".godot",
    ".export",
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


def _tracked_paths() -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z", "--", *TRACKED_ROOTS],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(
            "release packaging requires a Git checkout so only tracked files are bundled"
        ) from exc

    relative_paths: list[Path] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        try:
            relative_paths.append(Path(raw.decode("utf-8")))
        except UnicodeDecodeError as exc:
            raise ValueError("tracked release path is not valid UTF-8") from exc
    return relative_paths


def _allowed_relative_path(relative: Path) -> bool:
    posix = relative.as_posix()
    if any(posix.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return False
    if relative.name == "export.cfg":
        return False
    for part in relative.parts:
        if part in EXCLUDED_PARTS or part == ".env" or part.startswith(".env."):
            return False
    return relative.suffix not in EXCLUDED_SUFFIXES


def _safe_tracked_file(relative: Path) -> Path | None:
    if relative.is_absolute() or ".." in relative.parts or not _allowed_relative_path(relative):
        return None
    candidate = ROOT / relative
    if candidate.is_symlink():
        raise ValueError(f"release bundle refuses tracked symlink: {relative.as_posix()}")
    if not candidate.is_file():
        return None
    resolved = candidate.resolve(strict=True)
    root_resolved = ROOT.resolve(strict=True)
    if not resolved.is_relative_to(root_resolved):
        raise ValueError(f"release path escapes repository root: {relative.as_posix()}")
    return candidate


def release_files() -> list[Path]:
    files: list[Path] = []
    for relative in _tracked_paths():
        candidate = _safe_tracked_file(relative)
        if candidate is not None:
            files.append(candidate)
    unique = {path.relative_to(ROOT).as_posix(): path for path in files}
    return [unique[key] for key in sorted(unique)]


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
    if any(path.startswith("apps/godot-client/addons/godot-mcp/") for path in relative):
        raise ValueError("development Godot MCP addon must not be redistributed in v1 release bundle")


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
