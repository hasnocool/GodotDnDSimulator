# engine/src/godot_dnd_engine/rules/modifiers.py
"""Deterministic generic modifier pipeline with explicit stacking semantics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from itertools import groupby

from ..errors import ValidationError


class ModifierOperation(StrEnum):
    SET = "set"
    ADD = "add"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"


class StackingRule(StrEnum):
    STACK = "stack"
    HIGHEST = "highest"
    LOWEST = "lowest"
    REPLACE = "replace"


@dataclass(frozen=True, slots=True)
class RuleModifier:
    modifier_id: str
    value: int
    operation: ModifierOperation = ModifierOperation.ADD
    priority: int = 0
    stacking_key: str | None = None
    stacking_rule: StackingRule = StackingRule.STACK
    source_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.modifier_id, str) or not self.modifier_id.strip():
            raise ValidationError("modifier_id must be a non-empty string")
        if isinstance(self.value, bool) or not isinstance(self.value, int):
            raise ValidationError("modifier value must be an integer")
        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise ValidationError("modifier priority must be an integer")
        if self.stacking_key is not None and (
            not isinstance(self.stacking_key, str) or not self.stacking_key.strip()
        ):
            raise ValidationError("stacking_key must be None or a non-empty string")
        if self.source_id is not None and (
            not isinstance(self.source_id, str) or not self.source_id.strip()
        ):
            raise ValidationError("source_id must be None or a non-empty string")


@dataclass(frozen=True, slots=True)
class ModifierResolution:
    base_value: int
    final_value: int
    applied: tuple[RuleModifier, ...]
    suppressed: tuple[RuleModifier, ...]


def _choose_group(group: tuple[RuleModifier, ...]) -> tuple[RuleModifier, ...]:
    rules = {modifier.stacking_rule for modifier in group}
    if len(rules) != 1:
        key = group[0].stacking_key
        raise ValidationError(f"stacking group {key!r} mixes stacking rules")
    rule = next(iter(rules))
    if rule is StackingRule.STACK:
        return group
    if rule is StackingRule.HIGHEST:
        return (max(group, key=lambda item: (item.value, item.priority, item.modifier_id)),)
    if rule is StackingRule.LOWEST:
        return (min(group, key=lambda item: (item.value, -item.priority, item.modifier_id)),)
    return (max(group, key=lambda item: (item.priority, item.modifier_id)),)


def resolve_modifiers(base_value: int, modifiers: tuple[RuleModifier, ...]) -> ModifierResolution:
    if isinstance(base_value, bool) or not isinstance(base_value, int):
        raise ValidationError("modifier base value must be an integer")

    ungrouped = tuple(modifier for modifier in modifiers if modifier.stacking_key is None)
    grouped_input = sorted(
        (modifier for modifier in modifiers if modifier.stacking_key is not None),
        key=lambda item: (item.stacking_key or "", item.modifier_id),
    )
    selected: list[RuleModifier] = list(ungrouped)
    suppressed: list[RuleModifier] = []
    for _, group_iter in groupby(grouped_input, key=lambda item: item.stacking_key):
        group = tuple(group_iter)
        chosen = _choose_group(group)
        selected.extend(chosen)
        chosen_ids = {item.modifier_id for item in chosen}
        suppressed.extend(item for item in group if item.modifier_id not in chosen_ids)

    operation_order = {
        ModifierOperation.SET: 0,
        ModifierOperation.ADD: 1,
        ModifierOperation.MINIMUM: 2,
        ModifierOperation.MAXIMUM: 3,
    }
    applied = tuple(
        sorted(
            selected,
            key=lambda item: (item.priority, operation_order[item.operation], item.modifier_id),
        )
    )
    value = base_value
    for modifier in applied:
        if modifier.operation is ModifierOperation.SET:
            value = modifier.value
        elif modifier.operation is ModifierOperation.ADD:
            value += modifier.value
        elif modifier.operation is ModifierOperation.MINIMUM:
            value = max(value, modifier.value)
        else:
            value = min(value, modifier.value)

    return ModifierResolution(
        base_value=base_value,
        final_value=value,
        applied=applied,
        suppressed=tuple(sorted(suppressed, key=lambda item: item.modifier_id)),
    )
