from __future__ import annotations

from dataclasses import replace

import pytest
from godot_dnd_engine.actors import (
    ACTOR_SCHEMA_VERSION,
    SKILL_ABILITIES,
    ActorKind,
    ActorState,
    CharacterCreationRequest,
    CharacterCreationSpec,
    CharacterOption,
    ChoiceGroup,
    DefenseState,
    EquipmentAssignment,
    HitPoints,
    InventoryEntry,
    MovementMode,
    MovementSpeed,
    SaveProficiency,
    Sense,
    SizeCategory,
    Skill,
    SkillProficiency,
    TrainingProficiency,
    actor_from_dict,
    actor_to_dict,
    actors_to_rule_world,
    apply_actor_effects,
    create_character,
    deserialize_actor,
    merge_rule_world,
    migrate_actor_payload,
    serialize_actor,
    validate_choices,
)
from godot_dnd_engine.errors import ValidationError
from godot_dnd_engine.rules.effects import EffectKind, RuleEffect
from godot_dnd_engine.rules.primitives import Ability, AbilityScore, ProficiencyRank, ResourcePool
from godot_dnd_engine.rules.state import ConditionInstance, RuleSubjectState, RuleWorldState
from godot_dnd_engine.rules.targets import TargetMode, TargetSelector


def abilities() -> tuple[AbilityScore, ...]:
    return tuple(AbilityScore(ability, 10 + index) for index, ability in enumerate(Ability))


def actor() -> ActorState:
    return ActorState(
        actor_id="actor:hero",
        name="Test Hero",
        kind=ActorKind.HERO,
        size=SizeCategory.MEDIUM,
        level=5,
        proficiency_bonus=3,
        abilities=abilities(),
        hit_points=HitPoints(24, 30, 4),
        defense=DefenseState(15),
        skills=(SkillProficiency(Skill.PERCEPTION), SkillProficiency(Skill.ATHLETICS)),
        saves=(SaveProficiency(Ability.WISDOM),),
        proficiencies=(TrainingProficiency("tool:artisan"),),
        movement=(MovementSpeed(MovementMode.WALK, 30), MovementSpeed(MovementMode.SWIM, 15)),
        senses=(Sense("normal_vision"), Sense("darkvision", 60)),
        inventory=(InventoryEntry("inv:pack", "item:pack", tags=frozenset({"container"})),),
        equipment=(EquipmentAssignment("back", "inv:pack"),),
        resources=(ResourcePool("heroic_inspiration", 1, 1),),
        conditions=(ConditionInstance("condition:test"),),
        selected_options=("species:test", "class:test"),
        tags=frozenset({"party"}),
    )


def test_shared_actor_model_covers_hero_npc_creature() -> None:
    base = actor()
    assert replace(base, kind=ActorKind.HERO).kind is ActorKind.HERO
    assert replace(base, kind=ActorKind.NPC).kind is ActorKind.NPC
    assert replace(base, kind=ActorKind.CREATURE, level=None).kind is ActorKind.CREATURE


def test_actor_skill_and_save_modifiers_use_v03_proficiency() -> None:
    value = actor()
    assert SKILL_ABILITIES[Skill.ATHLETICS] is Ability.STRENGTH
    athletics = value.ability_score(Ability.STRENGTH).modifier + 3
    assert value.skill_modifier(Skill.ATHLETICS) == athletics
    assert value.skill_modifier(Skill.ARCANA) == value.ability_score(Ability.INTELLIGENCE).modifier
    assert value.save_modifier(Ability.WISDOM) == value.ability_score(Ability.WISDOM).modifier + 3
    assert value.proficiency_rank("tool:artisan") is ProficiencyRank.FULL
    assert value.proficiency_rank("tool:missing") is ProficiencyRank.NONE


def test_actor_movement_senses_inventory_and_equipment() -> None:
    value = actor()
    assert value.movement_speed(MovementMode.WALK) == 30
    assert value.movement_speed(MovementMode.FLY) is None
    assert value.senses[0].sense_id == "darkvision"
    assert value.equipment[0].entry_id == "inv:pack"


def test_actor_rule_subject_adapter_roundtrip() -> None:
    value = actor()
    subject = value.to_rule_subject()
    assert "actor-kind:hero" in subject.tags
    changed = RuleSubjectState(
        subject_id=subject.subject_id,
        tags=subject.tags,
        resources=(ResourcePool("heroic_inspiration", 0, 1),),
        conditions=(),
    )
    updated = value.with_rule_subject(changed)
    assert updated.resources[0].current == 0
    assert updated.conditions == ()
    assert updated.inventory == value.inventory


def test_v03_effect_pipeline_updates_actor_resources_through_adapter() -> None:
    source = actor()
    target = replace(source, actor_id="actor:target", name="Target")
    effect = RuleEffect(
        "effect:spend",
        EffectKind.RESOURCE_DELTA,
        TargetSelector(TargetMode.SINGLE),
        resource_id="heroic_inspiration",
        amount=-1,
    )
    result = apply_actor_effects((source, target), source_id=source.actor_id, effects=(effect,))
    updated_target = next(item for item in result.actors if item.actor_id == "actor:target")
    assert updated_target.resources[0].current == 0
    assert result.applications[0].target_id == "actor:target"


def test_actor_world_adapter_requires_exact_actor_set() -> None:
    value = actor()
    world = actors_to_rule_world((value,))
    merged = merge_rule_world((value,), world)
    assert merged == (value,)
    with pytest.raises(ValidationError, match="exactly match"):
        merge_rule_world((value,), RuleWorldState(()))


def test_hit_points_are_state_not_damage_pipeline() -> None:
    hp = HitPoints(10, 20, 5)
    assert hp.with_current(9) == HitPoints(9, 20, 5)
    assert hp.with_temporary(2) == HitPoints(10, 20, 2)


@pytest.mark.parametrize("current,maximum,temp", [(-1, 10, 0), (11, 10, 0), (1, 0, 0), (1, 10, -1)])
def test_invalid_hit_points_fail_closed(current: int, maximum: int, temp: int) -> None:
    with pytest.raises(ValidationError):
        HitPoints(current, maximum, temp)


def test_equipment_must_reference_inventory() -> None:
    with pytest.raises(ValidationError, match="unknown inventory"):
        replace(actor(), equipment=(EquipmentAssignment("hand", "inv:missing"),))


def test_actor_requires_all_six_abilities_exactly_once() -> None:
    with pytest.raises(ValidationError, match="six abilities"):
        replace(actor(), abilities=abilities()[:-1])
    with pytest.raises(ValidationError, match="six abilities"):
        replace(actor(), abilities=(*abilities(), AbilityScore(Ability.STRENGTH, 10)))


def test_choice_groups_validate_cardinality_requirements_and_conflicts() -> None:
    options = (
        CharacterOption("class:one", "class", grants_tags=frozenset({"class-selected"})),
        CharacterOption("class:two", "class"),
        CharacterOption("feat:one", "feat", requires=frozenset({"class:one"})),
        CharacterOption("feat:two", "feat", conflicts=frozenset({"feat:one"})),
    )
    groups = (
        ChoiceGroup("class", ("class:one", "class:two"), 1, 1),
        ChoiceGroup("feat", ("feat:one", "feat:two"), 0, 1),
    )
    result = validate_choices(options, groups, ("class:one", "feat:one"))
    assert result.selected_option_ids == ("class:one", "feat:one")
    assert result.granted_tags == frozenset({"class-selected"})
    with pytest.raises(ValidationError, match=r"requires 1\.\.1"):
        validate_choices(options, groups, ())
    with pytest.raises(ValidationError, match=r"requires selections"):
        validate_choices(options, groups, ("class:two", "feat:one"))
    with pytest.raises(ValidationError):
        validate_choices(options, (), ("feat:one", "feat:two", "class:one"))


def creation_spec() -> CharacterCreationSpec:
    return CharacterCreationSpec(
        spec_id="creation:starter",
        kind=ActorKind.HERO,
        level=1,
        size=SizeCategory.MEDIUM,
        abilities=tuple(AbilityScore(ability, 10) for ability in Ability),
        maximum_hit_points=10,
        armor_class=12,
        movement=(MovementSpeed(MovementMode.WALK, 30),),
        options=(
            CharacterOption("species:a", "species", grants_tags=frozenset({"species:a"})),
            CharacterOption("species:b", "species"),
            CharacterOption("class:a", "class", grants_tags=frozenset({"class:a"})),
        ),
        choice_groups=(
            ChoiceGroup("species", ("species:a", "species:b")),
            ChoiceGroup("class", ("class:a",)),
        ),
        base_tags=frozenset({"player-character"}),
    )


def test_headless_character_creation_api() -> None:
    result = create_character(
        creation_spec(),
        CharacterCreationRequest("actor:new", " New Hero ", ("species:a", "class:a")),
    )
    assert result.actor.name == "New Hero"
    assert result.actor.level == 1
    assert result.actor.proficiency_bonus == 2
    assert result.actor.hit_points == HitPoints(10, 10)
    assert result.actor.selected_options == ("class:a", "species:a")
    assert result.actor.tags == frozenset({"player-character", "species:a", "class:a"})


def test_character_creation_rejects_unknown_or_incomplete_choices() -> None:
    with pytest.raises(ValidationError):
        create_character(
            creation_spec(),
            CharacterCreationRequest("actor:new", "Hero", ("species:a", "missing")),
        )
    with pytest.raises(ValidationError):
        create_character(
            creation_spec(),
            CharacterCreationRequest("actor:new", "Hero", ("species:a",)),
        )


def test_actor_serialization_is_canonical_and_roundtrips() -> None:
    value = actor()
    encoded = serialize_actor(value)
    assert deserialize_actor(encoded) == value
    assert serialize_actor(deserialize_actor(encoded)) == encoded
    assert actor_to_dict(value)["schema_version"] == ACTOR_SCHEMA_VERSION


def test_actor_v0_payload_migrates_to_v1() -> None:
    legacy = {
        "schema_version": 0,
        "id": "actor:legacy",
        "name": "Legacy",
        "type": "hero",
        "size": "medium",
        "level": 1,
        "proficiency_bonus": 2,
        "abilities": {ability.value: 10 for ability in Ability},
        "hp": {"current": 8, "max": 8, "temp": 0},
        "ac": 12,
        "speed": 30,
    }
    migrated = migrate_actor_payload(legacy)
    assert migrated["schema_version"] == 1
    restored = actor_from_dict(legacy)
    assert restored.actor_id == "actor:legacy"
    assert restored.movement_speed(MovementMode.WALK) == 30


def test_actor_serialization_rejects_unknown_schema_or_corruption() -> None:
    with pytest.raises(ValidationError, match="unsupported actor schema"):
        actor_from_dict({"schema_version": 99})
    with pytest.raises(ValidationError, match="valid JSON"):
        deserialize_actor("{")
    with pytest.raises(ValidationError, match="JSON object"):
        deserialize_actor("[]")


def test_actor_validation_rejects_duplicate_collections() -> None:
    value = actor()
    with pytest.raises(ValidationError, match="skill proficiencies"):
        replace(value, skills=(SkillProficiency(Skill.ARCANA), SkillProficiency(Skill.ARCANA)))
    with pytest.raises(ValidationError, match="movement modes"):
        replace(
            value,
            movement=(
                MovementSpeed(MovementMode.WALK, 30),
                MovementSpeed(MovementMode.WALK, 20),
            ),
        )
    with pytest.raises(ValidationError, match="senses"):
        replace(value, senses=(Sense("darkvision", 60), Sense("darkvision", 120)))
    with pytest.raises(ValidationError, match="selected character options"):
        replace(value, selected_options=("one", "one"))
