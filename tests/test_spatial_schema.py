from __future__ import annotations

import json
from pathlib import Path

from godot_dnd_engine.actors import (
    ActorKind,
    ActorState,
    DefenseState,
    HitPoints,
    MovementMode,
    MovementSpeed,
    SizeCategory,
)
from godot_dnd_engine.rules import Ability, AbilityScore
from godot_dnd_engine.spatial import (
    GridCell,
    SpatialPlacement,
    SpatialRuntime,
    SpatialState,
    SquareGridSpace,
    serialize_event,
)
from jsonschema import Draft202012Validator


SCHEMA_PATH = Path("schemas/v1/spatial-event.schema.json")


def _actor() -> ActorState:
    return ActorState(
        actor_id="actor:schema",
        name="Schema Fixture",
        kind=ActorKind.HERO,
        size=SizeCategory.MEDIUM,
        proficiency_bonus=2,
        abilities=tuple(AbilityScore(ability, 12) for ability in Ability),
        hit_points=HitPoints(10, 10),
        defense=DefenseState(12),
        movement=(MovementSpeed(MovementMode.WALK, 30),),
    )


def test_serialized_spatial_move_matches_v1_schema() -> None:
    state = SpatialState(
        SquareGridSpace("space:schema", 4, 2),
        (SpatialPlacement("actor:schema", GridCell(0, 0)),),
    )
    transition = SpatialRuntime().move_entity(
        state,
        _actor(),
        GridCell(2, 0),
        MovementMode.WALK,
    )
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    payload = json.loads(serialize_event(transition.event))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def test_spatial_schema_rejects_missing_path() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    invalid = {
        "sequence": 1,
        "event_type": "entity.moved",
        "entity_id": "actor:schema",
        "schema_version": 1,
        "payload": {
            "cost_feet": 5,
            "from_anchor": [0, 0],
            "movement_mode": "walk",
            "threat_entries": [],
            "threat_exits": [],
            "to_anchor": [1, 0],
        },
    }
    errors = list(Draft202012Validator(schema).iter_errors(invalid))
    assert errors
    assert any("path" in error.message for error in errors)
