# tests/test_character_creator.py
from __future__ import annotations

import pytest

from godot_dnd_engine.character_creator import (
    CharacterCreatorRuntime,
    CharacterCreatorService,
    CharacterDraft,
    demo_character_catalog,
)
from godot_dnd_engine.errors import ValidationError
from godot_dnd_engine.rules import Ability


def _runtime() -> CharacterCreatorRuntime:
    return CharacterCreatorRuntime(demo_character_catalog())


def _draft(*, class_id: str = "class:scholar") -> CharacterDraft:
    feature = "spellchoice:echo-burst" if class_id == "class:scholar" else "featurechoice:interpose"
    return CharacterDraft(
        actor_id="actor:creator-hero",
        name="Aster Vale",
        selected_choice_ids=(
            "species:riverborn",
            "background:archivist",
            class_id,
            "skill:arcana",
            "skill:perception",
            "equipment:explorer-kit",
            feature,
        ),
        ability_method_id="standard-array",
        base_ability_scores=(
            (Ability.STRENGTH, 8),
            (Ability.DEXTERITY, 14),
            (Ability.CONSTITUTION, 13),
            (Ability.INTELLIGENCE, 15),
            (Ability.WISDOM, 12),
            (Ability.CHARISMA, 10),
        ),
        appearance=(("hair", "dark"), ("portrait", "portrait:aster")),
        biography="A traveling researcher.",
        personality="Curious and deliberate.",
    )


def test_creator_schema_is_engine_generated_and_covers_all_steps() -> None:
    schema = _runtime().schema()
    assert schema["catalog_id"] == "catalog:original-v0.9-demo"
    assert schema["steps"][0] == "identity"
    assert "review" in schema["steps"]
    choices = schema["choices"]
    assert any(item["choice_id"] == "species:riverborn" for item in choices)
    assert all(item["unlock_level"] == 1 for item in choices)


def test_preview_and_create_apply_choice_bundles_to_shared_actor_state() -> None:
    runtime = _runtime()
    draft = _draft()
    preview = runtime.preview(draft)
    assert preview["legal"] is True
    assert preview["summary"]["class_id"] == "class:scholar"

    record = runtime.create(draft)
    actor = record.actor
    assert actor.level == 1
    assert actor.name == "Aster Vale"
    assert actor.ability_score(Ability.DEXTERITY).score == 15
    assert actor.ability_score(Ability.WISDOM).score == 13
    assert record.species_id == "species:riverborn"
    assert record.background_id == "background:archivist"
    assert record.class_id == "class:scholar"
    assert "spell:arc-lance" in record.spell_ids
    assert "spell:echo-burst" in record.spell_ids
    assert "feature:prepared-study" in record.feature_ids
    assert actor.inventory
    assert actor.equipment


def test_creator_rejects_bad_group_cardinality_and_ability_assignment() -> None:
    runtime = _runtime()
    draft = _draft()
    with pytest.raises(ValidationError):
        runtime.create(
            CharacterDraft(
                actor_id=draft.actor_id,
                name=draft.name,
                selected_choice_ids=tuple(
                    item for item in draft.selected_choice_ids if item != "background:archivist"
                ),
                ability_method_id=draft.ability_method_id,
                base_ability_scores=draft.base_ability_scores,
            )
        )
    bad_scores = tuple(
        (ability, 10 if ability is Ability.STRENGTH else score)
        for ability, score in draft.base_ability_scores
    )
    invalid = CharacterDraft(
        actor_id=draft.actor_id,
        name=draft.name,
        selected_choice_ids=draft.selected_choice_ids,
        ability_method_id=draft.ability_method_id,
        base_ability_scores=bad_scores,
    )
    assert runtime.preview(invalid)["legal"] is False


def test_level_up_choices_and_transition_are_data_driven() -> None:
    runtime = _runtime()
    record = runtime.create(_draft())
    choices = runtime.level_up_choices(record)
    ids = {item["choice_id"] for item in choices["choices"]}
    assert ids == {"advance:scholar-binding-haze"}

    advanced = runtime.level_up(record, ("advance:scholar-binding-haze",))
    assert advanced.actor.level == 2
    assert advanced.actor.hit_points.maximum > record.actor.hit_points.maximum
    assert "spell:binding-haze" in advanced.spell_ids
    assert "advance:scholar-binding-haze" in advanced.actor.selected_options


def test_service_stores_created_records_and_rejects_duplicate_actor_ids() -> None:
    service = CharacterCreatorService(_runtime())
    draft = _draft()
    payload = {
        "actor_id": draft.actor_id,
        "name": draft.name,
        "selected_choice_ids": list(draft.selected_choice_ids),
        "ability_method_id": draft.ability_method_id,
        "ability_scores": {ability.value: score for ability, score in draft.base_ability_scores},
        "appearance": dict(draft.appearance),
        "biography": draft.biography,
        "personality": draft.personality,
    }
    result = service.command("characters.create", payload)
    assert result["record"]["actor"]["actor_id"] == draft.actor_id
    fetched = service.query("characters.get", {"actor_id": draft.actor_id})
    assert fetched["record"]["personality"] == "Curious and deliberate."
    with pytest.raises(ValidationError):
        service.command("characters.create", payload)
