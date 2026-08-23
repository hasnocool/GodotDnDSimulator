from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from godot_dnd_engine.serialization import dumps_canonical
from godot_dnd_engine.world import WorldRuntime, demo_campaign

ROOT = Path(__file__).resolve().parents[1]


def test_godot_world_save_envelope_matches_versioned_schema() -> None:
    schema = json.loads(
        (ROOT / "schemas/v1/godot-world-save-envelope.schema.json").read_text(
            encoding="utf-8"
        )
    )
    validator = Draft202012Validator(schema)
    runtime = WorldRuntime(demo_campaign(), seed=17)
    runtime.handle_command(
        "world.start",
        {"party_ids": ["actor:save-schema-hero"]},
        expected_sequence=0,
    )
    snapshot = runtime.snapshot()
    envelope = {
        "format": "godot-dnd-world-save",
        "format_version": 1,
        "slot_id": "slot-1",
        "metadata": {
            "saved_at": "2026-08-22 18:00:00",
            "campaign_id": runtime.definition.campaign_id,
            "sequence": runtime.state.sequence,
            "area_id": runtime.state.current_area_id,
            "area_name": next(
                area.name
                for area in runtime.definition.areas
                if area.area_id == runtime.state.current_area_id
            ),
        },
        "world_snapshot_json": dumps_canonical(snapshot),
    }

    assert list(validator.iter_errors(envelope)) == []
    decoded = json.loads(envelope["world_snapshot_json"])
    assert decoded["rng"] == snapshot["rng"]
