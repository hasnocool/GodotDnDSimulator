# tests/test_schema_contracts.py
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from godot_dnd_engine.engine import SimulationEngine
from godot_dnd_engine.models import CommandEnvelope
from godot_dnd_engine.serialization import event_to_dict, snapshot_to_dict

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "v1"


def _load_schema(name: str) -> dict[str, object]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def test_all_v1_schemas_are_valid_draft_2020_12() -> None:
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)


def test_emitted_event_and_snapshot_validate_against_schemas() -> None:
    engine = SimulationEngine.create(
        campaign_id="campaign:test",
        session_id="session:test",
        seed=5,
    )
    event = engine.handle(
        CommandEnvelope(
            command_id="command:roll",
            campaign_id="campaign:test",
            session_id="session:test",
            actor_id="actor:hero",
            command_type="simulation.roll_dice",
            payload={
                "expression": "1d20",
                "counter": "last",
                "reason": "schema test",
            },
        )
    )[0]

    Draft202012Validator(_load_schema("event.schema.json")).validate(event_to_dict(event))
    Draft202012Validator(_load_schema("snapshot.schema.json")).validate(
        snapshot_to_dict(engine.snapshot())
    )
