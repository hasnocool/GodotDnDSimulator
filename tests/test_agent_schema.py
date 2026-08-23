from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from godot_dnd_engine.agent_autoplay import create_autoplay_session

ROOT = Path(__file__).resolve().parents[1]


def _schema(path: str) -> dict[str, object]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_agent_observation_matches_versioned_schema() -> None:
    validator = Draft202012Validator(
        _schema("schemas/agent/v1/agent-observation.schema.json")
    )
    observation = create_autoplay_session(seed=31).agent.observe()

    assert list(validator.iter_errors(observation)) == []


def test_ui_automation_request_schema_accepts_narrow_rpc_surface() -> None:
    validator = Draft202012Validator(
        _schema("schemas/client/v1/ui-automation-request.schema.json")
    )
    request = {
        "id": "agent-1",
        "token": "local-debug-token",
        "method": "ui.activate",
        "params": {"path": "/root/GodotDnDSimulator/AppShell/SomeButton"},
    }

    assert list(validator.iter_errors(request)) == []
    invalid = dict(request)
    invalid["method"] = "ui.call_arbitrary_method"
    assert list(validator.iter_errors(invalid))
