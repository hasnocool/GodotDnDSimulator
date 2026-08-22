# engine/src/godot_dnd_engine/spatial/reducer.py
"""Pure reducers for versioned spatial events."""

from __future__ import annotations

from ..actors import MovementMode
from ..errors import ValidationError
from .events import SpatialEvent, SpatialEventValue
from .model import GridCell, MovementPolicy, SpatialState
from .movement import validate_path


def _cell(value: SpatialEventValue, label: str) -> GridCell:
    if not isinstance(value, tuple) or len(value) != 2:
        raise ValidationError(f"spatial event {label} must be a cell pair")
    x, y = value
    if (
        isinstance(x, bool)
        or not isinstance(x, int)
        or isinstance(y, bool)
        or not isinstance(y, int)
    ):
        raise ValidationError(f"spatial event {label} coordinates must be integers")
    return GridCell(x, y)


def _path(value: SpatialEventValue) -> tuple[GridCell, ...]:
    if not isinstance(value, tuple):
        raise ValidationError("spatial event path must be a tuple")
    return tuple(_cell(item, "path cell") for item in value)


def _integer(value: SpatialEventValue, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(f"spatial event {label} must be an integer >= 0")
    return value


def _string(value: SpatialEventValue, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"spatial event {label} must be a non-empty string")
    return value


def apply_spatial_event(
    state: SpatialState,
    event: SpatialEvent,
    *,
    policy: MovementPolicy = MovementPolicy(),
) -> SpatialState:
    if event.sequence != state.sequence + 1:
        raise ValidationError("spatial event sequence must be contiguous")
    if event.event_type != "entity.moved":
        raise ValidationError(f"unsupported spatial event type: {event.event_type}")

    placement = state.placement(event.entity_id)
    from_anchor = _cell(event.value("from_anchor"), "from_anchor")
    to_anchor = _cell(event.value("to_anchor"), "to_anchor")
    path = _path(event.value("path"))
    mode_value = _string(event.value("movement_mode"), "movement_mode")
    cost_feet = _integer(event.value("cost_feet"), "cost_feet")
    try:
        mode = MovementMode(mode_value)
    except ValueError as exc:
        raise ValidationError("spatial event movement_mode is unsupported") from exc

    if placement.anchor != from_anchor:
        raise ValidationError("spatial event from_anchor does not match current state")
    if not path or path[0] != from_anchor or path[-1] != to_anchor:
        raise ValidationError("spatial event path endpoints do not match movement anchors")
    validation = validate_path(state, event.entity_id, path, mode, policy=policy)
    if not validation.legal:
        raise ValidationError(f"spatial replay path is illegal: {validation.reason}")
    if validation.cost_feet != cost_feet:
        raise ValidationError("spatial event movement cost does not match path")
    return state.with_anchor(event.entity_id, to_anchor, sequence=event.sequence)
