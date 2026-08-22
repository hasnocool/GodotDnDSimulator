# engine/src/godot_dnd_engine/spatial/replay.py
"""Deterministic spatial replay from an initial logical state plus ordered events."""

from __future__ import annotations

from .events import SpatialEvent
from .model import SpatialState
from .reducer import apply_spatial_event


def replay_spatial(
    initial_state: SpatialState,
    events: tuple[SpatialEvent, ...],
) -> SpatialState:
    state = initial_state
    for event in events:
        state = apply_spatial_event(state, event)
    return state
