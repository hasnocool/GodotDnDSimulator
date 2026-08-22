from __future__ import annotations

import pytest
from godot_dnd_engine.errors import ValidationError
from godot_dnd_engine.rules import (
    ModifierOperation,
    RuleModifier,
    StackingRule,
    resolve_modifiers,
)


def test_modifier_pipeline_stacks_and_resolves_groups_deterministically() -> None:
    modifiers = (
        RuleModifier("modifier:set", 10, ModifierOperation.SET, priority=-10),
        RuleModifier("modifier:add", 2),
        RuleModifier(
            "modifier:cover-low",
            1,
            stacking_key="cover",
            stacking_rule=StackingRule.HIGHEST,
        ),
        RuleModifier(
            "modifier:cover-high",
            3,
            stacking_key="cover",
            stacking_rule=StackingRule.HIGHEST,
        ),
        RuleModifier("modifier:min", 16, ModifierOperation.MINIMUM, priority=10),
        RuleModifier("modifier:max", 18, ModifierOperation.MAXIMUM, priority=20),
    )
    result = resolve_modifiers(7, modifiers)
    assert result.final_value == 16
    assert [item.modifier_id for item in result.suppressed] == ["modifier:cover-low"]
    assert "modifier:cover-high" in {item.modifier_id for item in result.applied}


def test_replace_group_uses_priority_then_id() -> None:
    result = resolve_modifiers(
        10,
        (
            RuleModifier(
                "modifier:a",
                2,
                stacking_key="stance",
                stacking_rule=StackingRule.REPLACE,
                priority=1,
            ),
            RuleModifier(
                "modifier:b",
                4,
                stacking_key="stance",
                stacking_rule=StackingRule.REPLACE,
                priority=2,
            ),
        ),
    )
    assert result.final_value == 14
    assert [item.modifier_id for item in result.suppressed] == ["modifier:a"]


def test_mixed_stacking_rules_are_rejected() -> None:
    with pytest.raises(ValidationError, match="mixes stacking rules"):
        resolve_modifiers(
            10,
            (
                RuleModifier(
                    "modifier:a",
                    1,
                    stacking_key="same",
                    stacking_rule=StackingRule.HIGHEST,
                ),
                RuleModifier(
                    "modifier:b",
                    2,
                    stacking_key="same",
                    stacking_rule=StackingRule.STACK,
                ),
            ),
        )
