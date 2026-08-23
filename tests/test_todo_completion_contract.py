from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_backlog_completion_document_tracks_evidence_boundaries() -> None:
    text = (ROOT / "docs/TODO_BACKLOG_COMPLETION.md").read_text(encoding="utf-8")
    assert "v1.0 authored tactical encounters" in text
    assert "Exact-head executable gates" in text
    assert "Official SRD production audit" in text
    assert "Conditional save-product work" in text


def test_local_ci_registers_new_backlog_headless_suites() -> None:
    text = (ROOT / "scripts/local_ci.sh").read_text(encoding="utf-8")
    for suite in (
        "todo_backlog_tests.gd",
        "navigation_debug_tests.gd",
        "debug_identity_tests.gd",
        "spell_palette_grouping_tests.gd",
    ):
        assert suite in text
