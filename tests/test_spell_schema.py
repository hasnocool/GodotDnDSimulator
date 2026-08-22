# tests/test_spell_schema.py
from __future__ import annotations

import json
from pathlib import Path

from godot_dnd_engine.spells import SpellEvent, spell_event_to_dict
from jsonschema import Draft202012Validator


SCHEMA_PATH = Path("schemas/v1/spell-event.schema.json")


def test_serialized_spell_event_matches_v1_schema() -> None:
    event = SpellEvent(
        sequence=1,
        event_type="spell.cast",
        caster_id="actor:caster",
        spell_id="spell:fixture",
        target_ids=("actor:target",),
        payload=(("slot_level", 2), ("concentration", False)),
    )
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(spell_event_to_dict(event))


def test_spell_event_schema_rejects_duplicate_targets_and_unknown_fields() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    invalid = {
        "version": 1,
        "sequence": 1,
        "event_type": "spell.cast",
        "caster_id": "actor:caster",
        "spell_id": "spell:fixture",
        "target_ids": ["actor:target", "actor:target"],
        "payload": {},
        "unexpected": True,
    }
    errors = list(Draft202012Validator(schema).iter_errors(invalid))
    assert errors
