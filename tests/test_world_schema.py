# tests/test_world_schema.py
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from godot_dnd_engine.world import WorldRuntime, demo_campaign, event_to_dict

ROOT = Path(__file__).resolve().parents[1]


def test_world_events_match_versioned_schema() -> None:
    schema = json.loads(
        (ROOT / "schemas/v1/world-event.schema.json").read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(schema)
    runtime = WorldRuntime(demo_campaign(), seed=5)
    runtime.handle_command(
        "world.start",
        {"party_ids": ["actor:schema-hero"]},
        expected_sequence=0,
    )
    runtime.handle_command(
        "world.travel",
        {"area_id": "area:old-road"},
        expected_sequence=1,
    )
    runtime.handle_command(
        "world.resolve_interaction",
        {"interaction_id": "interaction:collapsed-marker", "bonus": 2},
        expected_sequence=2,
    )

    for event in runtime.events:
        errors = list(validator.iter_errors(event_to_dict(event)))
        assert errors == []
