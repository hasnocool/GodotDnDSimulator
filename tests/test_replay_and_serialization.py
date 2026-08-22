# tests/test_replay_and_serialization.py
from __future__ import annotations

import json

import pytest

from godot_dnd_engine.engine import SimulationEngine
from godot_dnd_engine.errors import SequenceError, ValidationError
from godot_dnd_engine.models import CommandEnvelope, GameState
from godot_dnd_engine.replay import replay_events
from godot_dnd_engine.serialization import (
    dumps_canonical,
    event_from_dict,
    event_to_dict,
    state_from_dict,
    state_to_dict,
)


def test_snapshot_and_event_log_reconstruct_exact_state() -> None:
    initial = GameState(campaign_id="campaign:test", session_id="session:test")
    engine = SimulationEngine.create(campaign_id="campaign:test", session_id="session:test", seed=123)

    events = []
    events.extend(
        engine.handle(
            CommandEnvelope(
                command_id="command:roll-1",
                campaign_id="campaign:test",
                session_id="session:test",
                actor_id="actor:hero",
                command_type="simulation.roll_dice",
                expected_sequence=0,
                payload={"expression": "2d6+2", "counter": "damage", "reason": "fixture"},
            )
        )
    )
    events.extend(
        engine.handle(
            CommandEnvelope(
                command_id="command:tick-1",
                campaign_id="campaign:test",
                session_id="session:test",
                command_type="simulation.advance_tick",
                expected_sequence=1,
                payload={"amount": 3},
            )
        )
    )

    encoded_events = [dumps_canonical(event_to_dict(event)) for event in events]
    decoded_events = [event_from_dict(json.loads(item)) for item in encoded_events]
    replayed = replay_events(state_from_dict(state_to_dict(initial)), decoded_events)

    assert replayed == engine.state
    assert replayed.sequence == 2
    assert replayed.tick == 3


def test_replay_rejects_event_gap() -> None:
    engine = SimulationEngine.create(campaign_id="campaign:test", session_id="session:test", seed=2)
    event = engine.handle(
        CommandEnvelope(
            command_id="command:tick",
            campaign_id="campaign:test",
            session_id="session:test",
            command_type="simulation.advance_tick",
        )
    )[0]
    wrong_start = GameState(campaign_id="campaign:test", session_id="session:test", sequence=2)
    with pytest.raises(SequenceError):
        replay_events(wrong_start, [event])


@pytest.mark.parametrize(
    "snapshot",
    [
        {},
        {"schema_version": 99},
        {
            "schema_version": 1,
            "campaign_id": "campaign:test",
            "session_id": "session:test",
            "sequence": "0",
            "tick": 0,
            "counters": {},
        },
        {
            "schema_version": 1,
            "campaign_id": "campaign:test",
            "session_id": "session:test",
            "sequence": 0,
            "tick": 0,
            "counters": {"x": True},
        },
    ],
)
def test_corrupted_snapshot_is_rejected(snapshot: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        state_from_dict(snapshot)
