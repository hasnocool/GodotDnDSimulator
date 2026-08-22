from __future__ import annotations

import pytest

from godot_dnd_engine.errors import ValidationError
from godot_dnd_engine.rng import DeterministicRNG
from godot_dnd_engine.rules import (
    Ability,
    AbilityScore,
    ConditionInstance,
    ConditionStacking,
    D20TestKind,
    DifficultyClass,
    Duration,
    DurationUnit,
    EffectKind,
    ProficiencyRank,
    ReactionHook,
    Requirement,
    RequirementKind,
    ResolutionContext,
    ResourceCost,
    ResourcePool,
    RollMode,
    RuleEffect,
    RuleEventView,
    RuleModifier,
    RuleSubjectState,
    RuleWorldState,
    RulesRuntime,
    RulesetCapabilities,
    StackingRule,
    TargetMode,
    TargetSelector,
    Trigger,
    apply_effects,
    proficiency_bonus_for_level,
    resolve_modifiers,
)


@pytest.mark.parametrize("level", [0, 21, True, 1.5])
def test_invalid_levels(level: object) -> None:
    with pytest.raises(ValidationError):
        proficiency_bonus_for_level(level)  # type: ignore[arg-type]


@pytest.mark.parametrize("bonus", [-1, 21, True, 1.5])
def test_invalid_proficiency_bonus(bonus: object) -> None:
    with pytest.raises(ValidationError):
        ProficiencyRank.FULL.apply(bonus)  # type: ignore[arg-type]


@pytest.mark.parametrize("counts", [(-1, 0), (0, -1), (True, 0), (0, 1.5)])
def test_invalid_roll_mode_sources(counts: tuple[object, object]) -> None:
    with pytest.raises(ValidationError):
        RollMode.from_sources(counts[0], counts[1])  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [-1, 1001, True, 2.5])
def test_invalid_difficulty_classes(value: object) -> None:
    with pytest.raises(ValidationError):
        DifficultyClass(value)  # type: ignore[arg-type]


def test_resource_validation_edges() -> None:
    with pytest.raises(ValidationError):
        ResourcePool("", 0, 1)
    with pytest.raises(ValidationError):
        ResourcePool("resource:x", 0, -1)
    with pytest.raises(ValidationError):
        ResourcePool("resource:x", 2, 1)
    with pytest.raises(ValidationError):
        ResourcePool("resource:x", True, 1)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        ResourcePool("resource:x", 0, 1).with_delta(True)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        ResourceCost("", 1)


def test_modifier_validation_and_lowest_group() -> None:
    with pytest.raises(ValidationError):
        RuleModifier("", 1)
    with pytest.raises(ValidationError):
        RuleModifier("modifier:x", True)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        RuleModifier("modifier:x", 1, stacking_key="")
    with pytest.raises(ValidationError):
        RuleModifier("modifier:x", 1, source_id="")
    with pytest.raises(ValidationError):
        resolve_modifiers(True, ())  # type: ignore[arg-type]

    result = resolve_modifiers(
        10,
        (
            RuleModifier(
                "modifier:a",
                -1,
                stacking_key="penalty",
                stacking_rule=StackingRule.LOWEST,
            ),
            RuleModifier(
                "modifier:b",
                -3,
                stacking_key="penalty",
                stacking_rule=StackingRule.LOWEST,
            ),
        ),
    )
    assert result.final_value == 7


def test_duration_condition_and_state_validation_edges() -> None:
    with pytest.raises(ValidationError):
        Duration(DurationUnit.PERMANENT, 1)
    with pytest.raises(ValidationError):
        Duration(DurationUnit.ROUNDS, None)
    with pytest.raises(ValidationError):
        Duration(DurationUnit.ROUNDS, 1).advance(-1)
    assert Duration(DurationUnit.ROUNDS, 1).advance(0) == Duration(DurationUnit.ROUNDS, 1)

    with pytest.raises(ValidationError):
        ConditionInstance("")
    with pytest.raises(ValidationError):
        ConditionInstance("condition:x", source_id="")
    with pytest.raises(ValidationError):
        ConditionInstance("condition:x", stacks=0)
    with pytest.raises(ValidationError):
        RuleSubjectState("")
    with pytest.raises(ValidationError):
        RuleSubjectState("actor:x", tags=frozenset({""}))
    with pytest.raises(ValidationError):
        RuleSubjectState(
            "actor:x",
            resources=(ResourcePool("resource:x", 1, 1), ResourcePool("resource:x", 1, 1)),
        )
    with pytest.raises(ValidationError):
        RuleWorldState((RuleSubjectState("actor:x"), RuleSubjectState("actor:x")))
    with pytest.raises(ValidationError):
        RuleWorldState((RuleSubjectState("actor:x"),)).subject("actor:missing")
    with pytest.raises(ValidationError):
        RuleWorldState((RuleSubjectState("actor:x"),)).replace_subject(
            RuleSubjectState("actor:missing")
        )


def test_selector_effect_hook_and_capability_validation_edges() -> None:
    with pytest.raises(ValidationError):
        TargetSelector(
            TargetMode.ALL,
            required_tags=frozenset({"same"}),
            excluded_tags=frozenset({"same"}),
        )
    with pytest.raises(ValidationError):
        TargetSelector(TargetMode.ALL, max_targets=0)
    with pytest.raises(ValidationError):
        TargetSelector(TargetMode.SELF, max_targets=2)
    with pytest.raises(ValidationError):
        TargetSelector(TargetMode.SINGLE, max_targets=2)

    selector = TargetSelector(TargetMode.SELF)
    with pytest.raises(ValidationError):
        RuleEffect("", EffectKind.RESOURCE_DELTA, selector, resource_id="resource:x")
    with pytest.raises(ValidationError):
        RuleEffect("effect:x", EffectKind.RESOURCE_DELTA, selector)
    with pytest.raises(ValidationError):
        RuleEffect(
            "effect:x",
            EffectKind.APPLY_CONDITION,
            selector,
            resource_id="resource:x",
            condition_id="condition:x",
        )
    with pytest.raises(ValidationError):
        RuleEffect("effect:x", EffectKind.APPLY_CONDITION, selector)

    with pytest.raises(ValidationError):
        RuleEventView("")
    with pytest.raises(ValidationError):
        Trigger("")
    with pytest.raises(ValidationError):
        ReactionHook("", "actor:x", Trigger("event:x"))
    with pytest.raises(ValidationError):
        ReactionHook("hook:x", "", Trigger("event:x"))
    with pytest.raises(ValidationError):
        ReactionHook(
            "hook:x",
            "actor:x",
            Trigger("event:x"),
            priority=True,  # type: ignore[arg-type]
        )

    with pytest.raises(ValidationError):
        RulesetCapabilities("", "1", frozenset())
    with pytest.raises(ValidationError):
        RulesetCapabilities("ruleset:x", "", frozenset())
    with pytest.raises(ValidationError):
        RulesetCapabilities("ruleset:x", "1", frozenset({""}))


def test_effect_batch_is_atomic_from_callers_perspective() -> None:
    world = RuleWorldState(
        (
            RuleSubjectState(
                "actor:a",
                resources=(ResourcePool("resource:focus", 0, 1),),
            ),
        )
    )
    effects = (
        RuleEffect(
            "effect:ok",
            EffectKind.APPLY_CONDITION,
            TargetSelector(TargetMode.SELF),
            condition_id="condition:temporary",
            condition_stacking=ConditionStacking.REFRESH,
        ),
        RuleEffect(
            "effect:bad",
            EffectKind.RESOURCE_DELTA,
            TargetSelector(TargetMode.SELF),
            resource_id="resource:focus",
            amount=-1,
        ),
    )
    with pytest.raises(ValidationError):
        apply_effects(world, source_id="actor:a", effects=effects)
    assert not world.subject("actor:a").has_condition("condition:temporary")

    with pytest.raises(ValidationError, match="unique effect IDs"):
        apply_effects(
            world,
            source_id="actor:a",
            effects=(effects[0], effects[0]),
        )


def test_runtime_facade_delegates_all_generic_subsystems() -> None:
    runtime = RulesRuntime(
        DeterministicRNG.from_seed(7), RulesetCapabilities.srd_5_2_1_core()
    )
    hero = RuleSubjectState(
        "actor:hero",
        tags=frozenset({"ally"}),
        resources=(ResourcePool("resource:focus", 2, 2),),
    )
    other = RuleSubjectState("actor:other", tags=frozenset({"ally"}))
    world = RuleWorldState((hero, other))

    spent = runtime.spend_resources(hero, (ResourceCost("resource:focus", 1),))
    assert spent.subject.resource("resource:focus").current == 1  # type: ignore[union-attr]
    checked = runtime.check_requirements(
        hero, (Requirement("requirement:ally", RequirementKind.TAG_PRESENT, "ally"),)
    )
    assert checked.passed
    targets = runtime.targets(
        world,
        "actor:hero",
        TargetSelector(TargetMode.SINGLE, required_tags=frozenset({"ally"})),
    )
    assert targets[0].subject_id == "actor:other"
    effected = runtime.apply_effects(
        world,
        source_id="actor:hero",
        effects=(
            RuleEffect(
                "effect:condition",
                EffectKind.APPLY_CONDITION,
                TargetSelector(TargetMode.SELF),
                condition_id="condition:ready",
            ),
        ),
    )
    assert effected.world.subject("actor:hero").has_condition("condition:ready")
    reactions = runtime.reactions(
        RuleEventView("event:test"),
        (ReactionHook("hook:test", "actor:hero", Trigger("event:test")),),
        world,
    )
    assert reactions[0].hook.hook_id == "hook:test"


def test_resolution_context_and_runtime_validation_edges() -> None:
    with pytest.raises(ValidationError):
        ResolutionContext(
            "",
            D20TestKind.ABILITY_CHECK,
            actor_id="actor:x",
            ability=Ability.STRENGTH,
        )
    with pytest.raises(ValidationError):
        ResolutionContext(
            "resolution:x",
            D20TestKind.ABILITY_CHECK,
            actor_id="",
            ability=Ability.STRENGTH,
        )
    with pytest.raises(ValidationError):
        ResolutionContext(
            "resolution:x",
            D20TestKind.ABILITY_CHECK,
            actor_id="actor:x",
            target_id="",
            ability=Ability.STRENGTH,
        )
    with pytest.raises(ValidationError):
        ResolutionContext(
            "resolution:x",
            D20TestKind.ABILITY_CHECK,
            actor_id="actor:x",
            ability=Ability.STRENGTH,
            reason="",
        )

    runtime = RulesRuntime(
        DeterministicRNG.from_seed(1), RulesetCapabilities.srd_5_2_1_core()
    )
    context = ResolutionContext(
        "resolution:x",
        D20TestKind.ABILITY_CHECK,
        actor_id="actor:x",
        ability=Ability.STRENGTH,
    )
    with pytest.raises(ValidationError, match="does not match"):
        runtime.resolve_d20(
            context,
            ability_score=AbilityScore(Ability.DEXTERITY, 10),
            proficiency_bonus=2,
        )

    save_without_dc = ResolutionContext(
        "resolution:save",
        D20TestKind.SAVING_THROW,
        actor_id="actor:x",
        ability=Ability.STRENGTH,
    )
    with pytest.raises(ValidationError, match="difficulty class"):
        runtime.resolve_save(
            save_without_dc,
            ability_score=AbilityScore(Ability.STRENGTH, 10),
            proficiency_bonus=2,
        )
