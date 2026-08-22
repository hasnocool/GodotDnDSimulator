from __future__ import annotations

import pytest
from godot_dnd_engine.errors import ValidationError
from godot_dnd_engine.rules import (
    ConditionInstance,
    ConditionStacking,
    Duration,
    DurationUnit,
    EffectKind,
    ResourceCost,
    ResourcePool,
    RuleEffect,
    RuleSubjectState,
    RuleWorldState,
    TargetMode,
    TargetSelector,
    advance_condition_durations,
    apply_effects,
    spend_costs,
)


def _world() -> RuleWorldState:
    return RuleWorldState(
        (
            RuleSubjectState(
                "actor:hero",
                tags=frozenset({"ally", "living"}),
                resources=(ResourcePool("resource:focus", 3, 3),),
            ),
            RuleSubjectState(
                "actor:other",
                tags=frozenset({"ally", "living"}),
                resources=(ResourcePool("resource:focus", 1, 3),),
            ),
        )
    )


def test_duration_expires_purely() -> None:
    duration = Duration(DurationUnit.ROUNDS, 2)
    assert duration.advance(1) == Duration(DurationUnit.ROUNDS, 1)
    assert duration.advance(2) is None
    permanent = Duration(DurationUnit.PERMANENT, None)
    assert permanent.advance(99) is permanent


def test_resource_costs_are_aggregated_and_atomic() -> None:
    hero = _world().subject("actor:hero")
    spent = spend_costs(
        hero,
        (ResourceCost("resource:focus", 1), ResourceCost("resource:focus", 1)),
    )
    assert spent.subject.resource("resource:focus").current == 1  # type: ignore[union-attr]
    assert spent.spent == (ResourceCost("resource:focus", 2),)

    with pytest.raises(ValidationError):
        spend_costs(hero, (ResourceCost("resource:focus", 4),))
    assert hero.resource("resource:focus").current == 3  # type: ignore[union-attr]


def test_effect_pipeline_resource_and_condition_lifecycle() -> None:
    selector = TargetSelector(TargetMode.SINGLE, required_tags=frozenset({"ally"}))
    effects = (
        RuleEffect(
            "effect:focus",
            EffectKind.RESOURCE_DELTA,
            selector,
            resource_id="resource:focus",
            amount=1,
        ),
        RuleEffect(
            "effect:condition",
            EffectKind.APPLY_CONDITION,
            selector,
            condition_id="condition:ready",
            duration=Duration(DurationUnit.ROUNDS, 2),
            condition_stacking=ConditionStacking.REFRESH,
        ),
    )
    result = apply_effects(_world(), source_id="actor:hero", effects=effects)
    other = result.world.subject("actor:other")
    assert other.resource("resource:focus").current == 2  # type: ignore[union-attr]
    assert other.has_condition("condition:ready")
    assert len(result.applications) == 2

    removed = apply_effects(
        result.world,
        source_id="actor:hero",
        effects=(
            RuleEffect(
                "effect:remove",
                EffectKind.REMOVE_CONDITION,
                selector,
                condition_id="condition:ready",
            ),
        ),
    )
    assert not removed.world.subject("actor:other").has_condition("condition:ready")


def test_unique_and_stack_condition_semantics() -> None:
    selector = TargetSelector(TargetMode.SELF)
    initial = RuleWorldState(
        (
            RuleSubjectState(
                "actor:hero",
                conditions=(ConditionInstance("condition:marked", stacks=1),),
            ),
        )
    )
    unique = apply_effects(
        initial,
        source_id="actor:hero",
        effects=(
            RuleEffect(
                "effect:unique",
                EffectKind.APPLY_CONDITION,
                selector,
                condition_id="condition:marked",
                condition_stacking=ConditionStacking.UNIQUE,
            ),
        ),
    )
    assert len(unique.world.subject("actor:hero").conditions) == 1

    stacked = apply_effects(
        unique.world,
        source_id="actor:hero",
        effects=(
            RuleEffect(
                "effect:stack",
                EffectKind.APPLY_CONDITION,
                selector,
                condition_id="condition:marked",
                condition_stacking=ConditionStacking.STACK,
                stacks=2,
            ),
        ),
    )
    assert sum(item.stacks for item in stacked.world.subject("actor:hero").conditions) == 3


def test_advancing_condition_durations_expires_only_matching_unit() -> None:
    subject = RuleSubjectState(
        "actor:hero",
        conditions=(
            ConditionInstance(
                "condition:short",
                duration=Duration(DurationUnit.ROUNDS, 1),
            ),
            ConditionInstance(
                "condition:long",
                duration=Duration(DurationUnit.ROUNDS, 3),
            ),
            ConditionInstance(
                "condition:turn",
                duration=Duration(DurationUnit.TURNS, 1),
            ),
        ),
    )
    updated = advance_condition_durations(subject, DurationUnit.ROUNDS)
    assert not updated.has_condition("condition:short")
    long_condition = next(
        item for item in updated.conditions if item.condition_id == "condition:long"
    )
    assert long_condition.duration == Duration(DurationUnit.ROUNDS, 2)
    assert updated.has_condition("condition:turn")
