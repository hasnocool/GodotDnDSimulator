# engine/src/godot_dnd_engine/reducer.py
"""Pure deterministic event reducers."""

from __future__ import annotations

from .errors import SequenceError, ValidationError
from .models import EventEnvelope, GameState


def apply_event(state: GameState, event: EventEnvelope) -> GameState:
    """Apply exactly one ordered domain event to state without external I/O."""

    if event.campaign_id != state.campaign_id or event.session_id != state.session_id:
        raise ValidationError("event campaign/session does not match state")
    expected_sequence = state.sequence + 1
    if event.sequence != expected_sequence:
        raise SequenceError(
            f"expected event sequence {expected_sequence}, received {event.sequence}"
        )
    if event.tick < state.tick:
        raise SequenceError("event tick cannot move simulation time backwards")

    if event.event_type == "dice.rolled":
        counter = event.payload.get("counter")
        total = event.payload.get("total")
        if not isinstance(counter, str) or not counter:
            raise ValidationError("dice.rolled event requires a counter name")
        if isinstance(total, bool) or not isinstance(total, int):
            raise ValidationError("dice.rolled event requires integer total")
        return state.with_counter(counter, total, sequence=event.sequence, tick=event.tick)

    if event.event_type == "simulation.tick_advanced":
        return GameState(
            campaign_id=state.campaign_id,
            session_id=state.session_id,
            sequence=event.sequence,
            tick=event.tick,
            counters=state.counters,
        )

    raise ValidationError(f"unsupported event type: {event.event_type!r}")
