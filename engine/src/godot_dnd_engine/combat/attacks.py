"""Typed abstract attack definitions and deterministic attack outcomes."""

from __future__ import annotations

from dataclasses import dataclass

from ..dice import DiceExpression
from ..errors import ValidationError
from ..rules.modifiers import RuleModifier
from ..rules.primitives import Ability, ProficiencyRank
from ..rules.runtime import D20Outcome
from .damage import DamageAdjustment
from .model import ActionResource


@dataclass(frozen=True, slots=True)
class AttackDefinition:
    attack_id: str
    ability: Ability
    proficiency_rank: ProficiencyRank
    damage_dice: DiceExpression
    damage_type: str
    damage_bonus: int = 0
    add_ability_to_damage: bool = True
    action_resource: ActionResource = ActionResource.ACTION

    def __post_init__(self) -> None:
        if not isinstance(self.attack_id, str) or not self.attack_id.strip():
            raise ValidationError("attack_id must be a non-empty string")
        if self.damage_dice.modifier != 0:
            raise ValidationError("attack damage_dice modifier must be 0; use damage_bonus")
        if not isinstance(self.damage_type, str) or not self.damage_type.strip():
            raise ValidationError("attack damage_type must be a non-empty string")
        if isinstance(self.damage_bonus, bool) or not isinstance(self.damage_bonus, int):
            raise ValidationError("damage_bonus must be an integer")
        if self.action_resource is ActionResource.REACTION:
            raise ValidationError("reaction attacks must be resolved through a reaction window")


@dataclass(frozen=True, slots=True)
class AttackResult:
    attack_id: str
    attacker_id: str
    target_id: str
    d20: D20Outcome
    target_armor_class: int
    hit: bool
    critical: bool
    damage_raw_rolls: tuple[int, ...]
    damage_before_defenses: int
    damage_adjustment: DamageAdjustment | None


@dataclass(frozen=True, slots=True)
class AttackModifiers:
    attack_roll: tuple[RuleModifier, ...] = ()
    advantage_sources: int = 0
    disadvantage_sources: int = 0
