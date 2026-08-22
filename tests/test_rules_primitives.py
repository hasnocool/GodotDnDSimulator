from __future__ import annotations

import pytest
from godot_dnd_engine.errors import ValidationError
from godot_dnd_engine.rules import (
    Ability,
    AbilityScore,
    DifficultyClass,
    ProficiencyRank,
    ResourceCost,
    ResourcePool,
    RollMode,
    proficiency_bonus_for_level,
)


@pytest.mark.parametrize(
    ("score", "expected"),
    [(1, -5), (2, -4), (9, -1), (10, 0), (11, 0), (12, 1), (20, 5), (30, 10)],
)
def test_ability_modifier_table_formula(score: int, expected: int) -> None:
    assert AbilityScore(Ability.STRENGTH, score).modifier == expected


@pytest.mark.parametrize("score", [0, 31, True, 1.5])
def test_ability_score_rejects_invalid_values(score: object) -> None:
    with pytest.raises(ValidationError):
        AbilityScore(Ability.DEXTERITY, score)  # type: ignore[arg-type]


def test_proficiency_progression_and_multipliers() -> None:
    assert [proficiency_bonus_for_level(level) for level in (1, 4, 5, 8, 9, 13, 17, 20)] == [
        2,
        2,
        3,
        3,
        4,
        5,
        6,
        6,
    ]
    assert ProficiencyRank.NONE.apply(5) == 0
    assert ProficiencyRank.HALF.apply(5) == 2
    assert ProficiencyRank.FULL.apply(5) == 5
    assert ProficiencyRank.DOUBLE.apply(5) == 10


def test_advantage_and_disadvantage_sources_cancel_completely() -> None:
    assert RollMode.from_sources(3, 1) is RollMode.NORMAL
    assert RollMode.from_sources(1, 4) is RollMode.NORMAL
    assert RollMode.from_sources(2, 0) is RollMode.ADVANTAGE
    assert RollMode.from_sources(0, 2) is RollMode.DISADVANTAGE


def test_resource_pool_and_cost_validation() -> None:
    pool = ResourcePool("resource:focus", current=2, maximum=3)
    assert pool.with_delta(-1).current == 1
    assert pool.with_delta(1).current == 3
    with pytest.raises(ValidationError):
        pool.with_delta(-3)
    with pytest.raises(ValidationError):
        ResourceCost("resource:focus", -1)
    assert DifficultyClass(30).value == 30
