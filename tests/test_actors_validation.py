from __future__ import annotations

from dataclasses import replace

import pytest
from godot_dnd_engine.actors import (
    ActorKind,
    CharacterCreationRequest,
    CharacterCreationSpec,
    CharacterOption,
    ChoiceGroup,
    DefenseState,
    EquipmentAssignment,
    InventoryEntry,
    MovementMode,
    MovementSpeed,
    Sense,
    SizeCategory,
    TrainingProficiency,
    actor_from_dict,
    actor_to_dict,
    actors_to_rule_world,
    deserialize_actor,
    validate_choices,
)
from godot_dnd_engine.errors import ValidationError
from godot_dnd_engine.rules.primitives import Ability, AbilityScore


def base_spec(**changes: object) -> CharacterCreationSpec:
    values: dict[str, object] = {
        "spec_id": "creation:test",
        "kind": ActorKind.HERO,
        "level": 1,
        "size": SizeCategory.MEDIUM,
        "abilities": tuple(AbilityScore(ability, 10) for ability in Ability),
        "maximum_hit_points": 8,
        "armor_class": 10,
    }
    values.update(changes)
    return CharacterCreationSpec(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "factory",
    [
        lambda: CharacterOption("", "class"),
        lambda: CharacterOption("class:a", ""),
        lambda: CharacterOption("class:a", "class", grants_tags=frozenset({""})),
        lambda: CharacterOption("class:a", "class", conflicts=frozenset({"class:a"})),
        lambda: ChoiceGroup("", ("a",)),
        lambda: ChoiceGroup("g", ()),
        lambda: ChoiceGroup("g", ("a", "a")),
        lambda: ChoiceGroup("g", ("a",), 2, 1),
        lambda: ChoiceGroup("g", ("a",), 0, 2),
        lambda: InventoryEntry("", "item:a"),
        lambda: InventoryEntry("entry:a", ""),
        lambda: InventoryEntry("entry:a", "item:a", 0),
        lambda: EquipmentAssignment("", "entry:a"),
        lambda: EquipmentAssignment("slot:a", ""),
        lambda: MovementSpeed(MovementMode.WALK, -1),
        lambda: Sense(""),
        lambda: Sense("darkvision", -1),
        lambda: DefenseState(-1),
        lambda: TrainingProficiency(""),
    ],
)
def test_invalid_actor_primitives_fail_closed(factory: object) -> None:
    with pytest.raises(ValidationError):
        factory()  # type: ignore[operator]


def test_choice_validation_rejects_broken_catalogs_and_selections() -> None:
    duplicate = (CharacterOption("a", "x"), CharacterOption("a", "x"))
    with pytest.raises(ValidationError, match="unique option IDs"):
        validate_choices(duplicate, (), ())

    options = (CharacterOption("a", "x"), CharacterOption("b", "x"))
    with pytest.raises(ValidationError, match="unique group IDs"):
        validate_choices(
            options,
            (ChoiceGroup("g", ("a",), 0, 1), ChoiceGroup("g", ("b",), 0, 1)),
            (),
        )
    with pytest.raises(ValidationError, match="unknown options"):
        validate_choices(options, (ChoiceGroup("g", ("missing",)),), ())
    with pytest.raises(ValidationError, match="selected character option IDs"):
        validate_choices(options, (), ("a", "a"))
    with pytest.raises(ValidationError, match="unknown selected"):
        validate_choices(options, (), ("missing",))


def test_creation_spec_rejects_invalid_catalog_references() -> None:
    option = CharacterOption("a", "x", requires=frozenset({"missing"}))
    with pytest.raises(ValidationError, match="references unknown options"):
        base_spec(options=(option,))
    with pytest.raises(ValidationError, match="unknown options"):
        base_spec(
            options=(CharacterOption("a", "x"),),
            choice_groups=(ChoiceGroup("g", ("missing",)),),
        )
    with pytest.raises(ValidationError, match="unique group IDs"):
        base_spec(
            options=(CharacterOption("a", "x"),),
            choice_groups=(
                ChoiceGroup("g", ("a",), 0, 1),
                ChoiceGroup("g", ("a",), 0, 1),
            ),
        )


def test_creation_request_rejects_blank_identity() -> None:
    with pytest.raises(ValidationError):
        CharacterCreationRequest("", "Hero")
    with pytest.raises(ValidationError):
        CharacterCreationRequest("actor:a", "")


def test_actor_collection_and_subject_identity_validation() -> None:
    from test_actors import actor

    value = actor()
    with pytest.raises(ValidationError, match="unique actor IDs"):
        actors_to_rule_world((value, value))
    with pytest.raises(ValidationError, match="does not match"):
        value.with_rule_subject(value.to_rule_subject().__class__("actor:other"))


def test_actor_validation_rejects_duplicate_inventory_and_equipment_slots() -> None:
    from test_actors import actor

    value = actor()
    entry = InventoryEntry("entry:a", "item:a")
    with pytest.raises(ValidationError, match="unique entry IDs"):
        replace(value, inventory=(entry, entry), equipment=())
    inventory = (entry, InventoryEntry("entry:b", "item:b"))
    with pytest.raises(ValidationError, match="unique slot IDs"):
        replace(
            value,
            inventory=inventory,
            equipment=(
                EquipmentAssignment("hand", "entry:a"),
                EquipmentAssignment("hand", "entry:b"),
            ),
        )


def test_serialization_rejects_wrong_field_shapes() -> None:
    from test_actors import actor

    payload = actor_to_dict(actor())
    broken = dict(payload)
    broken["abilities"] = []
    with pytest.raises(ValidationError, match="abilities must be an object"):
        actor_from_dict(broken)

    broken = dict(payload)
    broken["skills"] = ["not-an-object"]
    with pytest.raises(ValidationError, match="array of objects"):
        actor_from_dict(broken)

    broken = dict(payload)
    broken["tags"] = [1]
    with pytest.raises(ValidationError, match="array of strings"):
        actor_from_dict(broken)

    with pytest.raises(ValidationError, match="serialized actor must be a string"):
        deserialize_actor(123)  # type: ignore[arg-type]


def test_legacy_payload_requires_objects() -> None:
    with pytest.raises(ValidationError, match="legacy actor payload"):
        actor_from_dict({"schema_version": 0, "abilities": [], "hp": {}})
