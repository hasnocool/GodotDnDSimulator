# engine/src/godot_dnd_engine/replay.py
"""Event-log replay helpers."""

from __future__ import annotations

from collections.abc import Iterable

from .models import EventEnvelope, GameState, SimulationSnapshot
from .reducer import apply_event


def replay_events(initial_state: GameState, events: Iterable[EventEnvelope]) -> GameState:
    """Reconstruct visible game state from an ordered event stream."""

    state = initial_state
    for event in events:
        state = apply_event(state, event)
    return state


def replay_snapshot(
    initial_snapshot: SimulationSnapshot,
    events: Iterable[EventEnvelope],
) -> SimulationSnapshot:
    """Reconstruct state and RNG position for deterministic continuation."""

    state = initial_snapshot.state
    rng = initial_snapshot.rng
    for event in events:
        state = apply_event(state, event)
        if event.rng_after is not None:
            rng = event.rng_after
    return SimulationSnapshot(state=state, rng=rng)
