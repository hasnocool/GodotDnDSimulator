# engine/src/godot_dnd_engine/replay.py
"""Event-log replay helpers."""

from __future__ import annotations

from collections.abc import Iterable

from .models import EventEnvelope, GameState
from .reducer import apply_event


def replay_events(initial_state: GameState, events: Iterable[EventEnvelope]) -> GameState:
    """Reconstruct state by applying ordered events to a trusted starting snapshot."""

    state = initial_state
    for event in events:
        state = apply_event(state, event)
    return state
