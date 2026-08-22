"""Core typed rule primitives for the v0.3 rules runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..errors import ValidationError


class Ability(StrEnum):
    STRENGTH = "strength"
    DEXTERITY = "dexterity"
    CONSTITUTION = "constitution"
    INTELLIGENCE = "intelligence"
    WISDOM = "wisdom"
    CHARISMA = "charisma"


@dataclass(frozen=True, slots=True)
class AbilityScore:
    ability: Ability
    score: int

    def __post_init__(self) -> None:
        if isinstance(self.score, bool) or not isinstance(self.score, int):
            raise ValidationError("ability score must be an integer")
        if not 1 <= self.score <= 30:
            raise ValidationError("ability score must be between 1 and 30")

    @property
    def modifier(self) -> int:
        return (self.score - 10) // 2


class ProficiencyRank(StrEnum):
    NONE = "none"
    HALF = "half"
    FULL = "full"
    DOUBLE = "double"

    def apply(self, proficiency_bonus: int) -> int:
        if isinstance(proficiency_bonus, bool) or not isinstance(proficiency_bonus, int):
            raise ValidationError("proficiency bonus must be an integer")
        if not 0 <= proficiency_bonus <= 20:
            raise ValidationError("proficiency bonus is outside supported range")
        if self is ProficiencyRank.NONE:
            return 0
        if self is ProficiencyRank.HALF:
            return proficiency_bonus // 2
        if self is ProficiencyRank.FULL:
            return proficiency_bonus
        return proficiency_bonus * 2


def proficiency_bonus_for_level(level: int) -> int:
    """Return the SRD character proficiency bonus for level 1 through 20."""

    if isinstance(level, bool) or not isinstance(level, int):
        raise ValidationError("level must be an integer")
    if not 1 <= level <= 20:
        raise ValidationError("level must be between 1 and 20")
    return 2 + (level - 1) // 4


class D20TestKind(StrEnum):
    ABILITY_CHECK = "ability_check"
    SAVING_THROW = "saving_throw"
    ATTACK_ROLL = "attack_roll"


class RollMode(StrEnum):
    NORMAL = "normal"
    ADVANTAGE = "advantage"
    DISADVANTAGE = "disadvantage"

    @classmethod
    def from_sources(cls, advantage_sources: int, disadvantage_sources: int) -> RollMode:
        for label, value in (
            ("advantage_sources", advantage_sources),
            ("disadvantage_sources", disadvantage_sources),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationError(f"{label} must be an integer >= 0")
        if advantage_sources and disadvantage_sources:
            return cls.NORMAL
        if advantage_sources:
            return cls.ADVANTAGE
        if disadvantage_sources:
            return cls.DISADVANTAGE
        return cls.NORMAL


@dataclass(frozen=True, slots=True)
class DifficultyClass:
    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, int):
            raise ValidationError("difficulty class must be an integer")
        if not 0 <= self.value <= 1_000:
            raise ValidationError("difficulty class is outside supported range")


@dataclass(frozen=True, slots=True)
class ResourcePool:
    resource_id: str
    current: int
    maximum: int
    minimum: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, str) or not self.resource_id.strip():
            raise ValidationError("resource_id must be a non-empty string")
        for label, value in (
            ("current", self.current),
            ("maximum", self.maximum),
            ("minimum", self.minimum),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError(f"resource {label} must be an integer")
        if self.minimum > self.maximum:
            raise ValidationError("resource minimum cannot exceed maximum")
        if not self.minimum <= self.current <= self.maximum:
            raise ValidationError("resource current value must be within its bounds")

    def with_delta(self, delta: int) -> ResourcePool:
        if isinstance(delta, bool) or not isinstance(delta, int):
            raise ValidationError("resource delta must be an integer")
        updated = self.current + delta
        if not self.minimum <= updated <= self.maximum:
            raise ValidationError(
                f"resource {self.resource_id!r} would leave bounds: {updated}"
            )
        return ResourcePool(
            resource_id=self.resource_id,
            current=updated,
            maximum=self.maximum,
            minimum=self.minimum,
        )


@dataclass(frozen=True, slots=True)
class ResourceCost:
    resource_id: str
    amount: int

    def __post_init__(self) -> None:
        if not isinstance(self.resource_id, str) or not self.resource_id.strip():
            raise ValidationError("cost resource_id must be a non-empty string")
        if isinstance(self.amount, bool) or not isinstance(self.amount, int) or self.amount < 0:
            raise ValidationError("resource cost amount must be an integer >= 0")
