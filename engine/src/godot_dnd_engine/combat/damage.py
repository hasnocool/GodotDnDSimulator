"""Generic deterministic damage/healing resolution for tactical combat."""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import ValidationError
from .model import DefenseProfile


@dataclass(frozen=True, slots=True)
class DamagePacket:
    amount: int
    damage_type: str

    def __post_init__(self) -> None:
        if isinstance(self.amount, bool) or not isinstance(self.amount, int) or self.amount < 0:
            raise ValidationError("damage amount must be an integer >= 0")
        if not isinstance(self.damage_type, str) or not self.damage_type.strip():
            raise ValidationError("damage_type must be a non-empty string")


@dataclass(frozen=True, slots=True)
class DamageAdjustment:
    raw_amount: int
    adjusted_amount: int
    immune: bool
    resistant: bool
    vulnerable: bool


def adjust_damage(packet: DamagePacket, defenses: DefenseProfile) -> DamageAdjustment:
    """Apply immunity, then SRD resistance, then vulnerability deterministically."""

    if packet.damage_type in defenses.immunities:
        return DamageAdjustment(packet.amount, 0, True, False, False)
    amount = packet.amount
    resistant = packet.damage_type in defenses.resistances
    vulnerable = packet.damage_type in defenses.vulnerabilities
    if resistant:
        amount //= 2
    if vulnerable:
        amount *= 2
    return DamageAdjustment(packet.amount, amount, False, resistant, vulnerable)
