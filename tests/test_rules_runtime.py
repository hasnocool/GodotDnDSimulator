from __future__ import annotations

import pytest
from godot_dnd_engine.errors import ValidationError
from godot_dnd_engine.rng import DeterministicRNG
from godot_dnd_engine.rules import (
    Ability,
    AbilityScore,
    D20TestKind,
    DifficultyClass,
    ModifierOperation,
    ProficiencyRank,
    ResolutionContext,
    RollMode,
    RuleModifier,
    RulesetCapabilities,
    RulesRuntime,
)


def _runtime(seed: int = 123) -> RulesRuntime:
    return RulesRuntime(DeterministicRNG.from_seed(seed), RulesetCapabilities.srd_5_2_1_core())


def test_d20_resolution_is_deterministic_and_auditable() -> None:
    context = ResolutionContext(
        "resolution:check",
        D20TestKind.ABILITY_CHECK,
        actor_id="actor:hero",
        ability=Ability.DEXTERITY,
        proficiency_rank=ProficiencyRank.FULL,
        difficulty_class=DifficultyClass(15),
        reason="fixture check",
    )
    first = _runtime(777).resolve_d20(
        context,
        ability_score=AbilityScore(Ability.DEXTERITY, 16),
        proficiency_bonus=3,
        modifiers=(RuleModifier("modifier:circumstance", 2),),
    )
    second = _runtime(777).resolve_d20(
        context,
        ability_score=AbilityScore(Ability.DEXTERITY, 16),
        proficiency_bonus=3,
        modifiers=(RuleModifier("modifier:circumstance", 2),),
    )
    assert first == second
    assert first.total == first.selected_roll + 3 + 3 + 2
    assert first.success is (first.total >= 15)
    assert first.rng_algorithm == "pcg32-v1"


def test_advantage_uses_higher_roll_and_disadvantage_uses_lower_roll() -> None:
    context = ResolutionContext(
        "resolution:adv",
        D20TestKind.ABILITY_CHECK,
        actor_id="actor:hero",
        ability=Ability.WISDOM,
    )
    advantage = _runtime(99).resolve_d20(
        context,
        ability_score=AbilityScore(Ability.WISDOM, 10),
        proficiency_bonus=2,
        advantage_sources=4,
    )
    disadvantage = _runtime(99).resolve_d20(
        context,
        ability_score=AbilityScore(Ability.WISDOM, 10),
        proficiency_bonus=2,
        disadvantage_sources=4,
    )
    cancelled = _runtime(99).resolve_d20(
        context,
        ability_score=AbilityScore(Ability.WISDOM, 10),
        proficiency_bonus=2,
        advantage_sources=5,
        disadvantage_sources=1,
    )
    assert advantage.roll_mode is RollMode.ADVANTAGE
    assert advantage.selected_roll == max(advantage.raw_rolls)
    assert disadvantage.roll_mode is RollMode.DISADVANTAGE
    assert disadvantage.selected_roll == min(disadvantage.raw_rolls)
    assert cancelled.roll_mode is RollMode.NORMAL
    assert len(cancelled.raw_rolls) == 1


def test_save_resolution_requires_save_context_and_dc() -> None:
    save = ResolutionContext(
        "resolution:save",
        D20TestKind.SAVING_THROW,
        actor_id="actor:hero",
        ability=Ability.CONSTITUTION,
        proficiency_rank=ProficiencyRank.FULL,
        difficulty_class=DifficultyClass(14),
    )
    result = _runtime().resolve_save(
        save,
        ability_score=AbilityScore(Ability.CONSTITUTION, 14),
        proficiency_bonus=3,
    )
    assert result.success is (result.total >= 14)

    not_save = ResolutionContext(
        "resolution:not-save",
        D20TestKind.ABILITY_CHECK,
        actor_id="actor:hero",
        ability=Ability.CONSTITUTION,
        difficulty_class=DifficultyClass(10),
    )
    with pytest.raises(ValidationError):
        _runtime().resolve_save(
            not_save,
            ability_score=AbilityScore(Ability.CONSTITUTION, 14),
            proficiency_bonus=3,
        )


def test_modifier_pipeline_can_bound_d20_total() -> None:
    context = ResolutionContext(
        "resolution:bounds",
        D20TestKind.ABILITY_CHECK,
        actor_id="actor:hero",
        ability=Ability.INTELLIGENCE,
    )
    outcome = _runtime(1).resolve_d20(
        context,
        ability_score=AbilityScore(Ability.INTELLIGENCE, 10),
        proficiency_bonus=2,
        modifiers=(RuleModifier("modifier:cap", 12, ModifierOperation.MAXIMUM),),
    )
    assert outcome.total <= 12


def test_attack_roll_does_not_preempt_v05_attack_resolution() -> None:
    context = ResolutionContext(
        "resolution:attack",
        D20TestKind.ATTACK_ROLL,
        actor_id="actor:hero",
        target_id="actor:target",
        ability=Ability.STRENGTH,
        difficulty_class=DifficultyClass(1),
    )
    outcome = _runtime(42).resolve_d20(
        context,
        ability_score=AbilityScore(Ability.STRENGTH, 18),
        proficiency_bonus=3,
    )
    assert outcome.selected_roll in range(1, 21)
    assert outcome.success is None


def test_ruleset_capabilities_fail_closed() -> None:
    limited = RulesetCapabilities("ruleset:test", "1", frozenset({"d20_tests"}))
    runtime = RulesRuntime(DeterministicRNG.from_seed(1), limited)
    context = ResolutionContext(
        "resolution:test",
        D20TestKind.ABILITY_CHECK,
        actor_id="actor:hero",
        ability=Ability.STRENGTH,
    )
    with pytest.raises(ValidationError, match="modifier_pipeline"):
        runtime.resolve_d20(
            context,
            ability_score=AbilityScore(Ability.STRENGTH, 10),
            proficiency_bonus=2,
        )
