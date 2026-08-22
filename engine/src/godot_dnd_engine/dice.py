# engine/src/godot_dnd_engine/dice.py
"""Deterministic dice expressions and audit-friendly roll results."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .errors import ValidationError
from .rng import DeterministicRNG

_DICE_RE = re.compile(r"^(?P<count>\d*)d(?P<sides>\d+)(?P<modifier>[+-]\d+)?$", re.I)


@dataclass(frozen=True, slots=True)
class DiceExpression:
    count: int
    sides: int
    modifier: int = 0

    def __post_init__(self) -> None:
        if isinstance(self.count, bool) or not isinstance(self.count, int):
            raise ValidationError("dice count must be an integer")
        if isinstance(self.sides, bool) or not isinstance(self.sides, int):
            raise ValidationError("dice sides must be an integer")
        if isinstance(self.modifier, bool) or not isinstance(self.modifier, int):
            raise ValidationError("dice modifier must be an integer")
        if not 1 <= self.count <= 100:
            raise ValidationError("dice count must be between 1 and 100")
        if not 2 <= self.sides <= 100_000:
            raise ValidationError("dice sides must be between 2 and 100000")
        if not -1_000_000 <= self.modifier <= 1_000_000:
            raise ValidationError("dice modifier is outside supported range")

    @classmethod
    def parse(cls, value: str) -> DiceExpression:
        if not isinstance(value, str):
            raise ValidationError("dice expression must be a string")
        compact = re.sub(r"\s+", "", value)
        match = _DICE_RE.fullmatch(compact)
        if match is None:
            raise ValidationError(f"invalid dice expression: {value!r}")
        count = int(match.group("count") or "1")
        sides = int(match.group("sides"))
        modifier = int(match.group("modifier") or "0")
        return cls(count=count, sides=sides, modifier=modifier)

    def canonical(self) -> str:
        suffix = "" if self.modifier == 0 else f"{self.modifier:+d}"
        return f"{self.count}d{self.sides}{suffix}"


@dataclass(frozen=True, slots=True)
class DiceRoll:
    expression: str
    raw_rolls: tuple[int, ...]
    modifier: int
    total: int
    reason: str
    actor_id: str | None
    target_id: str | None
    rng_algorithm: str

    def to_dict(self) -> dict[str, object]:
        return {
            "expression": self.expression,
            "raw_rolls": list(self.raw_rolls),
            "modifier": self.modifier,
            "total": self.total,
            "reason": self.reason,
            "actor_id": self.actor_id,
            "target_id": self.target_id,
            "rng_algorithm": self.rng_algorithm,
        }


def roll_expression(
    expression: DiceExpression,
    rng: DeterministicRNG,
    *,
    reason: str,
    actor_id: str | None = None,
    target_id: str | None = None,
) -> DiceRoll:
    if not isinstance(reason, str) or not reason.strip():
        raise ValidationError("roll reason must be a non-empty string")
    raw = tuple(rng.roll_die(expression.sides) for _ in range(expression.count))
    return DiceRoll(
        expression=expression.canonical(),
        raw_rolls=raw,
        modifier=expression.modifier,
        total=sum(raw) + expression.modifier,
        reason=reason.strip(),
        actor_id=actor_id,
        target_id=target_id,
        rng_algorithm=rng.ALGORITHM,
    )
