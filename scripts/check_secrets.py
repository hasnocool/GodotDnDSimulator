# scripts/check_secrets.py
"""High-signal repository secret scan for local CI and pull requests."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 2 * 1024 * 1024
TEXT_SUFFIXES = {
    "",
    ".cfg",
    ".gd",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".tscn",
    ".tres",
    ".txt",
    ".yaml",
    ".yml",
}
EXCLUDED_PARTS = {
    ".cache",
    ".git",
    ".godot",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
    "htmlcov",
}
PATTERNS = {
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "OpenAI API key": re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    "private key": re.compile("-----BEGIN " + "(?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def _candidate_files() -> list[Path]:
    rows: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in EXCLUDED_PARTS for part in path.relative_to(ROOT).parts):
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        rows.append(path)
    return sorted(rows)


def scan() -> list[str]:
    findings: list[str] = []
    for path in _candidate_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        relative = path.relative_to(ROOT).as_posix()
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{relative}:{line}: possible {label}")
    return findings


def main() -> int:
    findings = scan()
    if findings:
        print("Secret scan failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1
    print("Secret scan passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
