from __future__ import annotations

import json
from pathlib import Path

from godot_dnd_engine.diagnostics import JsonlDiagnosticWriter


def test_jsonl_diagnostic_writer_persists_structured_entries(tmp_path: Path) -> None:
    path = tmp_path / "diagnostics" / "engine.jsonl"
    writer = JsonlDiagnosticWriter(path)
    writer.write(
        "agent",
        "action accepted",
        actor_id="actor:test",
        sequence=7,
    )
    writer.write("bridge", "exchange", ok=True, operation="agent.observe")
    writer.close()

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [row["category"] for row in rows] == ["agent", "bridge"]
    assert rows[0]["actor_id"] == "actor:test"
    assert rows[0]["sequence"] == 7
    assert isinstance(rows[0]["timestamp_unix_ns"], int)
    assert rows[1]["ok"] is True
    assert rows[1]["operation"] == "agent.observe"


def test_jsonl_diagnostic_writer_close_is_idempotent(tmp_path: Path) -> None:
    writer = JsonlDiagnosticWriter(tmp_path / "engine.jsonl")
    writer.write("session", "start")
    writer.close()
    writer.close()

    assert (tmp_path / "engine.jsonl").read_text(encoding="utf-8").count("\n") == 1
