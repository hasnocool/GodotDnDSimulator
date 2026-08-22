# tests/test_character_schema.py
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from godot_dnd_engine.character_creator import (
    CharacterCreatorRuntime,
    CharacterDraft,
    demo_character_catalog,
    record_to_dict,
)
from godot_dnd_engine.rules import Ability

ROOT = Path(__file__).resolve().parents[1]


def test_created_character_record_matches_v1_schema() -> None:
    runtime = CharacterCreatorRuntime(demo_character_catalog())
    record = runtime.create(
        CharacterDraft(
            actor_id="actor:schema-hero",
            name="Schema Hero",
            selected_choice_ids=(
                "species:riverborn",
                "background:wayfarer",
                "class:guardian",
                "skill:athletics",
                "skill:insight",
                "equipment:defender-kit",
                "featurechoice:interpose",
            ),
            ability_method_id="standard-array",
            base_ability_scores=(
                (Ability.STRENGTH, 15),
                (Ability.DEXTERITY, 12),
                (Ability.CONSTITUTION, 14),
                (Ability.INTELLIGENCE, 8),
                (Ability.WISDOM, 13),
                (Ability.CHARISMA, 10),
            ),
        )
    )
    schema = json.loads((ROOT / "schemas/v1/character-record.schema.json").read_text())
    Draft202012Validator(schema).validate(record_to_dict(record))
