# engine/src/godot_dnd_engine/spells/state.py
"""Immutable spellcasting state and duration/concentration transitions."""

from __future__ import annotations

from dataclasses import dataclass, replace

from ..errors import ValidationError
from .model import ConcentrationState, SpellEffectSpec, SpellcastingState


@dataclass(frozen=True, slots=True)
class ActiveSpellEffect:
    effect_id: str
    spell_id: str
    caster_id: str
    target_ids: tuple[str, ...]
    effects: tuple[SpellEffectSpec, ...]
    remaining_rounds: int
    cast_level: int
    concentration: bool = False

    def __post_init__(self) -> None:
        if (
            not self.effect_id.strip()
            or not self.spell_id.strip()
            or not self.caster_id.strip()
        ):
            raise ValidationError("active spell IDs must be non-empty")
        if len(self.target_ids) != len(set(self.target_ids)):
            raise ValidationError("active spell target IDs must be unique")
        if any(not target.strip() for target in self.target_ids):
            raise ValidationError("active spell target IDs must be non-empty")
        if (
            isinstance(self.remaining_rounds, bool)
            or not isinstance(self.remaining_rounds, int)
            or self.remaining_rounds < 1
        ):
            raise ValidationError("active spell remaining_rounds must be an integer >= 1")
        if (
            isinstance(self.cast_level, bool)
            or not isinstance(self.cast_level, int)
            or not 0 <= self.cast_level <= 9
        ):
            raise ValidationError("active spell cast_level must be an integer from 0 through 9")

    def tick(self) -> ActiveSpellEffect | None:
        if self.remaining_rounds <= 1:
            return None
        return replace(self, remaining_rounds=self.remaining_rounds - 1)


@dataclass(frozen=True, slots=True)
class SpellRuntimeState:
    casters: tuple[SpellcastingState, ...] = ()
    active_effects: tuple[ActiveSpellEffect, ...] = ()
    sequence: int = 0

    def __post_init__(self) -> None:
        actor_ids = [item.actor_id for item in self.casters]
        if len(actor_ids) != len(set(actor_ids)):
            raise ValidationError("spell runtime casters must have unique actor IDs")
        effect_ids = [item.effect_id for item in self.active_effects]
        if len(effect_ids) != len(set(effect_ids)):
            raise ValidationError("active spell effects must have unique IDs")
        if (
            isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 0
        ):
            raise ValidationError("spell runtime sequence must be an integer >= 0")
        object.__setattr__(
            self,
            "casters",
            tuple(sorted(self.casters, key=lambda item: item.actor_id)),
        )
        object.__setattr__(
            self,
            "active_effects",
            tuple(sorted(self.active_effects, key=lambda item: item.effect_id)),
        )

    def caster(self, actor_id: str) -> SpellcastingState:
        match = next((item for item in self.casters if item.actor_id == actor_id), None)
        if match is None:
            raise ValidationError(f"actor has no spellcasting state: {actor_id}")
        return match

    def replace_caster(self, caster: SpellcastingState) -> SpellRuntimeState:
        if not any(item.actor_id == caster.actor_id for item in self.casters):
            raise ValidationError("cannot replace unknown spellcaster")
        return replace(
            self,
            casters=tuple(
                caster if item.actor_id == caster.actor_id else item
                for item in self.casters
            ),
        )

    def end_concentration(self, actor_id: str) -> SpellRuntimeState:
        caster = self.caster(actor_id)
        if caster.concentration is None:
            return self
        updated = replace(caster, concentration=None)
        effects = tuple(
            effect
            for effect in self.active_effects
            if not (effect.caster_id == actor_id and effect.concentration)
        )
        return replace(self.replace_caster(updated), active_effects=effects)

    def start_concentration(
        self,
        actor_id: str,
        concentration: ConcentrationState,
    ) -> SpellRuntimeState:
        state = self.end_concentration(actor_id)
        caster = state.caster(actor_id)
        return state.replace_caster(replace(caster, concentration=concentration))
