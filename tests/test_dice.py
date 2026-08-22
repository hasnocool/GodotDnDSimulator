# tests/test_dice.py
from __future__ import annotations

import pytest
from godot_dnd_engine.dice import DiceExpression, roll_expression
from godot_dnd_engine.errors import ValidationError
from godot_dnd_engine.rng import DeterministicRNG


@pytest.mark.parametrize(
    ("source", "canonical"),
    [
        ("d20", "1d20"),
        ("2d6+3", "2d6+3"),
        ("4D8-2", "4d8-2"),
        (" 1d12 +4 ", "1d12+4"),
    ],
)
def test_parse_and_canonicalize(source: str, canonical: str) -> None:
    assert DiceExpression.parse(source).canonical() == canonical


@pytest.mark.parametrize("source", ["", "20", "0d6", "1d1", "101d6", "d", "2d6++1"])
def test_invalid_dice_expression_rejected(source: str) -> None:
    with pytest.raises(ValidationError):
        DiceExpression.parse(source)


def test_roll_records_audit_metadata() -> None:
    rng = DeterministicRNG.from_seed(77)
    result = roll_expression(
        DiceExpression.parse("2d6+3"),
        rng,
        reason="attack damage",
        actor_id="actor:hero",
        target_id="actor:target",
    )
    assert len(result.raw_rolls) == 2
    assert all(1 <= value <= 6 for value in result.raw_rolls)
    assert result.total == sum(result.raw_rolls) + 3
    assert result.reason == "attack damage"
    assert result.actor_id == "actor:hero"
    assert result.target_id == "actor:target"
    assert result.rng_algorithm == "pcg32-v1"
