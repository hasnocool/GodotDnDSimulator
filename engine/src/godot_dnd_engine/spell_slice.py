# engine/src/godot_dnd_engine/spell_slice.py
"""v0.8 spell-enabled adapter over the v0.7 authoritative tactical slice."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .combat import EncounterState
from .dice import DiceExpression
from .errors import ValidationError
from .models import CommandEnvelope
from .rules import Ability
from .spells import (
    SaveEffect,
    SpellDefinition,
    SpellEffectKind,
    SpellEffectSpec,
    SpellQueryService,
    SpellResolution,
    SpellRuntime,
    SpellRuntimeState,
    SpellScaling,
    SpellSlotPool,
    SpellTargetKind,
    SpellcastingState,
)
from .spatial import GridCell, SpatialState
from .vertical_slice import TacticalCommandResult, TacticalVerticalSliceSession

SPELL_SLICE_CAPABILITIES = (
    "spells.runtime.v1",
    "spells.commands.v1",
    "spells.queries.v1",
    "spells.previews.v1",
)


@dataclass(slots=True)
class SpellEnabledTacticalSession:
    tactical: TacticalVerticalSliceSession
    spell_runtime: SpellRuntime
    spell_state: SpellRuntimeState

    @classmethod
    def create(
        cls,
        *,
        campaign_id: str,
        session_id: str,
        seed: int = 7,
    ) -> SpellEnabledTacticalSession:
        tactical = TacticalVerticalSliceSession.create(
            campaign_id=campaign_id,
            session_id=session_id,
            seed=seed,
        )
        definitions = demo_spell_definitions()
        spell_runtime = SpellRuntime(tactical.rng, definitions)
        spell_ids = tuple(item.spell_id for item in definitions)
        prepared_ids = tuple(
            item.spell_id for item in definitions if item.requires_preparation
        )
        spell_state = SpellRuntimeState(
            casters=tuple(
                SpellcastingState(
                    actor_id=combatant.actor.actor_id,
                    ability=Ability.INTELLIGENCE,
                    spell_attack_bonus=4,
                    spell_save_dc=12,
                    known_spell_ids=spell_ids,
                    prepared_spell_ids=prepared_ids,
                    slots=(
                        SpellSlotPool(1, 3, 3),
                        SpellSlotPool(2, 1, 1),
                    ),
                )
                for combatant in tactical.encounter.combatants
            )
        )
        return cls(tactical=tactical, spell_runtime=spell_runtime, spell_state=spell_state)

    @property
    def sequence(self) -> int:
        return self.tactical.sequence

    @property
    def encounter(self) -> EncounterState:
        return self.tactical.encounter

    @property
    def spatial(self) -> SpatialState:
        return self.tactical.spatial

    def snapshot(self) -> dict[str, object]:
        snapshot = self.tactical.snapshot()
        state_value = snapshot.get("state")
        if not isinstance(state_value, dict):
            raise ValidationError("tactical snapshot state is malformed")
        state = dict(state_value)
        tactical_value = state.get("tactical")
        if not isinstance(tactical_value, dict):
            raise ValidationError("tactical snapshot payload is malformed")
        tactical_state = dict(tactical_value)
        tactical_state["spellcasting"] = self._spell_snapshot()
        state["tactical"] = tactical_state
        snapshot["state"] = state
        return snapshot

    def query(self, query_type: str, payload: Mapping[str, Any]) -> dict[str, object]:
        if query_type == "tactical.snapshot":
            return {"snapshot": self.snapshot()}
        if query_type.startswith("spells."):
            return self._query_service().execute(query_type, dict(payload))
        return self.tactical.query(query_type, payload)

    def preview(self, preview_type: str, payload: Mapping[str, Any]) -> dict[str, object]:
        if preview_type == "spells.preview":
            return self._query_service().execute(preview_type, dict(payload))
        return self.tactical.preview(preview_type, payload)

    def handle_command(self, command: CommandEnvelope) -> TacticalCommandResult:
        if command.command_type == "tactical.cast_spell":
            return self._cast_spell(command)
        before_round = self.tactical.encounter.round_number
        result = self.tactical.handle_command(command)
        presentation_events = list(result.presentation_events)
        if (
            command.command_type == "tactical.end_turn"
            and self.tactical.encounter.round_number > before_round
            and self.tactical.encounter.status.value == "active"
        ):
            transition = self.spell_runtime.advance_round(
                self.spell_state,
                self.tactical.encounter,
            )
            self.spell_state = transition.spell_state
            self.tactical.encounter = transition.encounter
            presentation_events.extend(
                {
                    "sequence": self.tactical.sequence,
                    "type": "tactical.spell_duration_expired",
                    "actor_id": event.caster_id,
                    "payload": {"spell_id": event.spell_id},
                }
                for event in transition.events
                if event.event_type == "spell.duration.expired"
            )
        return TacticalCommandResult(
            snapshot=self.snapshot(),
            presentation_events=tuple(presentation_events),
            result=result.result,
        )

    def _cast_spell(self, command: CommandEnvelope) -> TacticalCommandResult:
        self.tactical._validate_command_envelope(command)
        caster_id = command.actor_id
        assert caster_id is not None
        spell_id = _string(command.payload.get("spell_id"), "spell_id")
        slot_level = _optional_int(command.payload.get("slot_level"), "slot_level")
        target_ids = _targets(command.payload.get("target_ids", []))
        point = _point(command.payload.get("point"))
        direction = _direction(
            command.payload.get("direction", {"x": 1.0, "y": 0.0})
        )
        definition = self.spell_runtime.definition(spell_id)
        transition = self.spell_runtime.cast(
            self.spell_state,
            self.tactical.encounter,
            self.tactical.spatial,
            caster_id=caster_id,
            spell_id=spell_id,
            slot_level=slot_level,
            target_ids=target_ids,
            point=point,
            direction=direction,
        )
        self.spell_state = transition.spell_state
        self.tactical.encounter = transition.encounter
        self.tactical.sequence += 1
        presentation = {
            "sequence": self.tactical.sequence,
            "type": "tactical.spell_resolved",
            "actor_id": caster_id,
            "payload": {
                "spell_id": spell_id,
                "slot_level": definition.cast_level(slot_level),
                "effect_kinds": [effect.kind.value for effect in definition.effects],
                "targets": [
                    {
                        "target_id": outcome.target_id,
                        "attack_total": outcome.attack_total,
                        "save_total": outcome.save_total,
                        "success": outcome.success,
                        "amounts": list(outcome.amounts),
                    }
                    for outcome in transition.outcomes
                ],
            },
        }
        self.tactical.recent_events.append(presentation)
        winner = self.tactical._winning_team()
        events: list[dict[str, object]] = [presentation]
        if winner is not None and self.tactical.encounter.status.value == "active":
            self.tactical.encounter = self.tactical.combat_runtime.end_encounter(
                self.tactical.encounter
            ).state
            ended = {
                "sequence": self.tactical.sequence,
                "type": "tactical.encounter_ended",
                "payload": {"winner_team": winner},
            }
            self.tactical.recent_events.append(ended)
            events.append(ended)
        return TacticalCommandResult(
            snapshot=self.snapshot(),
            presentation_events=tuple(events),
            result={"spell_id": spell_id, "outcome_count": len(transition.outcomes)},
        )

    def _query_service(self) -> SpellQueryService:
        return SpellQueryService(
            runtime=self.spell_runtime,
            state=self.spell_state,
            encounter=self.tactical.encounter,
            spatial=self.tactical.spatial,
        )

    def _spell_snapshot(self) -> dict[str, object]:
        return {
            "sequence": self.spell_state.sequence,
            "casters": [
                {
                    "actor_id": caster.actor_id,
                    "ability": caster.ability.value,
                    "spell_attack_bonus": caster.spell_attack_bonus,
                    "spell_save_dc": caster.spell_save_dc,
                    "known_spell_ids": list(caster.known_spell_ids),
                    "prepared_spell_ids": list(caster.prepared_spell_ids),
                    "slots": [
                        {
                            "level": slot.level,
                            "current": slot.current,
                            "maximum": slot.maximum,
                        }
                        for slot in caster.slots
                    ],
                    "concentration": (
                        None
                        if caster.concentration is None
                        else {
                            "spell_id": caster.concentration.spell_id,
                            "remaining_rounds": caster.concentration.remaining_rounds,
                        }
                    ),
                }
                for caster in self.spell_state.casters
            ],
            "active_effects": [
                {
                    "effect_id": effect.effect_id,
                    "spell_id": effect.spell_id,
                    "caster_id": effect.caster_id,
                    "target_ids": list(effect.target_ids),
                    "remaining_rounds": effect.remaining_rounds,
                    "concentration": effect.concentration,
                }
                for effect in self.spell_state.active_effects
            ],
        }


def demo_spell_definitions() -> tuple[SpellDefinition, ...]:
    """Original data-defined fixtures covering representative v0.8 effect families."""

    return (
        SpellDefinition(
            spell_id="spell:arc-lance",
            name="Arc Lance",
            level=0,
            resolution=SpellResolution.ATTACK,
            target_kind=SpellTargetKind.CREATURE,
            range_feet=60,
            requires_preparation=False,
            effects=(
                SpellEffectSpec(
                    SpellEffectKind.DAMAGE,
                    dice=DiceExpression(1, 8),
                    damage_type="damage:arcane",
                ),
            ),
        ),
        SpellDefinition(
            spell_id="spell:echo-burst",
            name="Echo Burst",
            level=1,
            resolution=SpellResolution.SAVE,
            save_ability=Ability.DEXTERITY,
            target_kind=SpellTargetKind.AREA,
            range_feet=30,
            area_shape="sphere",
            area_size_feet=10,
            effects=(
                SpellEffectSpec(
                    SpellEffectKind.DAMAGE,
                    dice=DiceExpression(2, 6),
                    damage_type="damage:resonance",
                    save_effect=SaveEffect.HALF,
                ),
            ),
            scaling=SpellScaling(extra_damage_dice_per_slot=1),
        ),
        SpellDefinition(
            spell_id="spell:binding-haze",
            name="Binding Haze",
            level=1,
            resolution=SpellResolution.SAVE,
            save_ability=Ability.WISDOM,
            target_kind=SpellTargetKind.AREA,
            range_feet=30,
            area_shape="sphere",
            area_size_feet=10,
            concentration=True,
            duration_rounds=3,
            effects=(
                SpellEffectSpec(
                    SpellEffectKind.CONDITION,
                    condition_id="condition:hindered",
                    save_effect=SaveEffect.NEGATES,
                ),
            ),
        ),
        SpellDefinition(
            spell_id="spell:resonant-field",
            name="Resonant Field",
            level=1,
            resolution=SpellResolution.AUTOMATIC,
            target_kind=SpellTargetKind.AREA,
            range_feet=30,
            area_shape="sphere",
            area_size_feet=10,
            concentration=True,
            duration_rounds=2,
            effects=(
                SpellEffectSpec(
                    SpellEffectKind.DAMAGE,
                    dice=DiceExpression(1, 4),
                    damage_type="damage:resonance",
                    ongoing=True,
                ),
            ),
        ),
        SpellDefinition(
            spell_id="spell:mending-light",
            name="Mending Light",
            level=1,
            resolution=SpellResolution.AUTOMATIC,
            target_kind=SpellTargetKind.SELF,
            range_feet=0,
            effects=(
                SpellEffectSpec(
                    SpellEffectKind.HEALING,
                    dice=DiceExpression(1, 8),
                    flat_amount=2,
                ),
            ),
            scaling=SpellScaling(extra_healing_dice_per_slot=1),
        ),
    )


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    return value


def _optional_int(value: Any, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(f"{label} must be None or an integer >= 0")
    return value


def _targets(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValidationError("target_ids must be an array")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValidationError("target_ids must contain non-empty strings")
    return tuple(value)


def _point(value: Any) -> GridCell | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValidationError("point must be null or a cell object")
    x = value.get("x")
    y = value.get("y")
    if isinstance(x, bool) or not isinstance(x, int) or isinstance(y, bool) or not isinstance(y, int):
        raise ValidationError("point.x/y must be integers")
    return GridCell(x, y)


def _direction(value: Any) -> tuple[float, float]:
    if not isinstance(value, Mapping):
        raise ValidationError("direction must be an object")
    x = value.get("x")
    y = value.get("y")
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise ValidationError("direction.x must be numeric")
    if isinstance(y, bool) or not isinstance(y, (int, float)):
        raise ValidationError("direction.y must be numeric")
    if float(x) == 0.0 and float(y) == 0.0:
        raise ValidationError("direction must not be zero")
    return float(x), float(y)
