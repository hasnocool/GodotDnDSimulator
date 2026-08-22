# engine/src/godot_dnd_engine/spells/model.py
"""Generic spellcasting domain contracts for v0.8."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from ..dice import DiceExpression
from ..errors import ValidationError
from ..rules.primitives import Ability


class SpellResolution(StrEnum):
    AUTOMATIC = "automatic"
    ATTACK = "attack"
    SAVE = "save"


class SpellTargetKind(StrEnum):
    SELF = "self"
    CREATURE = "creature"
    POINT = "point"
    AREA = "area"


class SpellEffectKind(StrEnum):
    DAMAGE = "damage"
    HEALING = "healing"
    CONDITION = "condition"
    REMOVE_CONDITION = "remove_condition"


class SaveEffect(StrEnum):
    NONE = "none"
    HALF = "half"
    NEGATES = "negates"


@dataclass(frozen=True, slots=True)
class SpellSlotPool:
    level: int
    current: int
    maximum: int

    def __post_init__(self) -> None:
        if isinstance(self.level, bool) or not isinstance(self.level, int) or not 1 <= self.level <= 9:
            raise ValidationError("spell slot level must be an integer from 1 through 9")
        for label, value in (("current", self.current), ("maximum", self.maximum)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationError(f"spell slot {label} must be an integer >= 0")
        if self.current > self.maximum:
            raise ValidationError("current spell slots cannot exceed maximum")

    def spend(self) -> SpellSlotPool:
        if self.current < 1:
            raise ValidationError(f"no level {self.level} spell slots remain")
        return replace(self, current=self.current - 1)


@dataclass(frozen=True, slots=True)
class ConcentrationState:
    spell_id: str
    caster_id: str
    remaining_rounds: int | None = None

    def __post_init__(self) -> None:
        if not self.spell_id.strip() or not self.caster_id.strip():
            raise ValidationError("concentration spell_id/caster_id must be non-empty")
        if self.remaining_rounds is not None and (
            isinstance(self.remaining_rounds, bool)
            or not isinstance(self.remaining_rounds, int)
            or self.remaining_rounds < 1
        ):
            raise ValidationError("concentration remaining_rounds must be None or >= 1")


@dataclass(frozen=True, slots=True)
class SpellcastingState:
    actor_id: str
    ability: Ability
    spell_attack_bonus: int
    spell_save_dc: int
    known_spell_ids: tuple[str, ...] = ()
    prepared_spell_ids: tuple[str, ...] = ()
    slots: tuple[SpellSlotPool, ...] = ()
    concentration: ConcentrationState | None = None

    def __post_init__(self) -> None:
        if not self.actor_id.strip():
            raise ValidationError("spellcasting actor_id must be non-empty")
        if isinstance(self.spell_attack_bonus, bool) or not isinstance(self.spell_attack_bonus, int):
            raise ValidationError("spell_attack_bonus must be an integer")
        if (
            isinstance(self.spell_save_dc, bool)
            or not isinstance(self.spell_save_dc, int)
            or self.spell_save_dc < 0
        ):
            raise ValidationError("spell_save_dc must be an integer >= 0")
        for label, values in (
            ("known", self.known_spell_ids),
            ("prepared", self.prepared_spell_ids),
        ):
            if len(values) != len(set(values)) or any(not item.strip() for item in values):
                raise ValidationError(f"{label} spell IDs must be unique non-empty strings")
        levels = [item.level for item in self.slots]
        if len(levels) != len(set(levels)):
            raise ValidationError("spell slot pools must be unique by level")
        object.__setattr__(self, "known_spell_ids", tuple(sorted(self.known_spell_ids)))
        object.__setattr__(self, "prepared_spell_ids", tuple(sorted(self.prepared_spell_ids)))
        object.__setattr__(self, "slots", tuple(sorted(self.slots, key=lambda item: item.level)))

    def can_cast(self, spell_id: str, *, requires_preparation: bool) -> bool:
        if spell_id not in self.known_spell_ids:
            return False
        return not requires_preparation or spell_id in self.prepared_spell_ids

    def slot(self, level: int) -> SpellSlotPool | None:
        return next((item for item in self.slots if item.level == level), None)

    def spend_slot(self, level: int) -> SpellcastingState:
        if level == 0:
            return self
        pool = self.slot(level)
        if pool is None:
            raise ValidationError(f"caster has no level {level} spell slot pool")
        slots = tuple(pool.spend() if item.level == level else item for item in self.slots)
        return replace(self, slots=slots)


@dataclass(frozen=True, slots=True)
class SpellScaling:
    extra_damage_dice_per_slot: int = 0
    extra_healing_dice_per_slot: int = 0
    extra_targets_per_slot: int = 0

    def __post_init__(self) -> None:
        for value in (
            self.extra_damage_dice_per_slot,
            self.extra_healing_dice_per_slot,
            self.extra_targets_per_slot,
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationError("spell scaling values must be integers >= 0")


@dataclass(frozen=True, slots=True)
class SpellEffectSpec:
    kind: SpellEffectKind
    dice: DiceExpression | None = None
    flat_amount: int = 0
    damage_type: str | None = None
    condition_id: str | None = None
    save_effect: SaveEffect = SaveEffect.NONE

    def __post_init__(self) -> None:
        if isinstance(self.flat_amount, bool) or not isinstance(self.flat_amount, int):
            raise ValidationError("spell effect flat_amount must be an integer")
        if self.kind is SpellEffectKind.DAMAGE and not self.damage_type:
            raise ValidationError("damage spell effects require damage_type")
        if self.kind in {SpellEffectKind.CONDITION, SpellEffectKind.REMOVE_CONDITION} and not self.condition_id:
            raise ValidationError("condition spell effects require condition_id")
        if self.dice is not None and self.dice.modifier != 0:
            raise ValidationError("spell effect dice modifier must be zero; use flat_amount")


@dataclass(frozen=True, slots=True)
class SpellDefinition:
    spell_id: str
    name: str
    level: int
    resolution: SpellResolution
    target_kind: SpellTargetKind
    effects: tuple[SpellEffectSpec, ...]
    range_feet: int = 0
    max_targets: int = 1
    requires_preparation: bool = True
    save_ability: Ability | None = None
    concentration: bool = False
    duration_rounds: int | None = None
    area_shape: str | None = None
    area_size_feet: int | None = None
    scaling: SpellScaling = SpellScaling()
    tags: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not self.spell_id.strip() or not self.name.strip():
            raise ValidationError("spell ID and name must be non-empty")
        if isinstance(self.level, bool) or not isinstance(self.level, int) or not 0 <= self.level <= 9:
            raise ValidationError("spell level must be an integer from 0 through 9")
        if isinstance(self.range_feet, bool) or not isinstance(self.range_feet, int) or self.range_feet < 0:
            raise ValidationError("spell range must be an integer >= 0")
        if isinstance(self.max_targets, bool) or not isinstance(self.max_targets, int) or self.max_targets < 1:
            raise ValidationError("spell max_targets must be an integer >= 1")
        if not self.effects:
            raise ValidationError("spell definitions require at least one generic effect")
        if self.resolution is SpellResolution.SAVE and self.save_ability is None:
            raise ValidationError("save spells require save_ability")
        if self.target_kind is SpellTargetKind.AREA:
            if self.area_shape not in {"sphere", "cube", "cylinder", "cone", "line"}:
                raise ValidationError("area spells require a supported generic area_shape")
            if self.area_size_feet is None or self.area_size_feet <= 0:
                raise ValidationError("area spells require area_size_feet > 0")
        if self.duration_rounds is not None and (
            isinstance(self.duration_rounds, bool)
            or not isinstance(self.duration_rounds, int)
            or self.duration_rounds < 1
        ):
            raise ValidationError("spell duration_rounds must be None or >= 1")

    def cast_level(self, requested_level: int | None) -> int:
        if self.level == 0:
            if requested_level not in (None, 0):
                raise ValidationError("cantrips do not consume higher-level slots")
            return 0
        level = self.level if requested_level is None else requested_level
        if isinstance(level, bool) or not isinstance(level, int) or not self.level <= level <= 9:
            raise ValidationError("cast slot level must be between spell level and 9")
        return level
