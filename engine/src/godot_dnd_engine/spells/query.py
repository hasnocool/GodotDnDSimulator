# engine/src/godot_dnd_engine/spells/query.py
"""JSON-shaped spell query surface for clients and tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..combat import EncounterState
from ..errors import UnsupportedCommandError, ValidationError
from ..spatial import GridCell, SpatialState
from .runtime import SpellRuntime
from .state import SpellRuntimeState


@dataclass(frozen=True, slots=True)
class SpellQueryService:
    runtime: SpellRuntime
    state: SpellRuntimeState
    encounter: EncounterState
    spatial: SpatialState

    def execute(self, query_type: str, payload: dict[str, Any]) -> dict[str, object]:
        if not isinstance(query_type, str) or not query_type.strip():
            raise ValidationError("spell query_type must be a non-empty string")
        if not isinstance(payload, dict):
            raise ValidationError("spell query payload must be an object")
        if query_type == "spells.available":
            actor_id = _string(payload.get("actor_id"), "actor_id")
            return {
                "actor_id": actor_id,
                "spells": list(self.runtime.available_spells(self.state, actor_id)),
                "slots": self._slots(actor_id),
                "concentration": self._concentration(actor_id),
                "active_effects": self._active_effects(actor_id),
            }
        if query_type == "spells.state":
            actor_id = _string(payload.get("actor_id"), "actor_id")
            return {
                "actor_id": actor_id,
                "slots": self._slots(actor_id),
                "concentration": self._concentration(actor_id),
                "active_effects": self._active_effects(actor_id),
            }
        if query_type == "spells.preview":
            caster_id = _string(payload.get("caster_id"), "caster_id")
            spell_id = _string(payload.get("spell_id"), "spell_id")
            slot_level = _optional_int(payload.get("slot_level"), "slot_level")
            targets = _string_tuple(payload.get("target_ids", []), "target_ids")
            point = _optional_cell(payload.get("point"))
            direction = _direction(payload.get("direction", {"x": 1.0, "y": 0.0}))
            return self.runtime.preview_cast(
                self.state,
                self.encounter,
                self.spatial,
                caster_id=caster_id,
                spell_id=spell_id,
                slot_level=slot_level,
                target_ids=targets,
                point=point,
                direction=direction,
            )
        raise UnsupportedCommandError(f"unsupported spell query: {query_type}")

    def _slots(self, actor_id: str) -> list[dict[str, int]]:
        return [
            {"level": item.level, "current": item.current, "maximum": item.maximum}
            for item in self.state.caster(actor_id).slots
        ]

    def _concentration(self, actor_id: str) -> dict[str, object] | None:
        concentration = self.state.caster(actor_id).concentration
        if concentration is None:
            return None
        return {
            "spell_id": concentration.spell_id,
            "caster_id": concentration.caster_id,
            "remaining_rounds": concentration.remaining_rounds,
        }

    def _active_effects(self, actor_id: str) -> list[dict[str, object]]:
        return [
            {
                "effect_id": item.effect_id,
                "spell_id": item.spell_id,
                "caster_id": item.caster_id,
                "target_ids": list(item.target_ids),
                "remaining_rounds": item.remaining_rounds,
                "concentration": item.concentration,
            }
            for item in self.state.active_effects
            if item.caster_id == actor_id or actor_id in item.target_ids
        ]


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("%s must be a non-empty string" % label)
    return value


def _optional_int(value: Any, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(f"{label} must be None or an integer >= 0")
    return value


def _string_tuple(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValidationError(f"{label} must be an array")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValidationError(f"{label} must contain non-empty strings")
    return tuple(value)


def _optional_cell(value: Any) -> GridCell | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValidationError("point must be null or a cell object")
    x = value.get("x")
    y = value.get("y")
    if isinstance(x, bool) or not isinstance(x, int) or isinstance(y, bool) or not isinstance(y, int):
        raise ValidationError("point x/y must be integers")
    return GridCell(x, y)


def _direction(value: Any) -> tuple[float, float]:
    if not isinstance(value, dict):
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
