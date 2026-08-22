# tests/test_engine_integration.py
from __future__ import annotations

import pytest

from godot_dnd_engine.engine import SimulationEngine
from godot_dnd_engine.errors import SequenceError, UnsupportedCommandError, ValidationError
from godot_dnd_engine.models import CommandEnvelope
from godot_dnd_engine.serialization import dumps_canonical, event_to_dict, state_to_dict


def _roll_command(*, expected_sequence: int = 0) -> CommandEnvelope:
    return CommandEnvelope(
        command_id="command:roll-0001",
        campaign_id="campaign:test",
        session_id="session:test",
        actor_id="actor:hero",
        command_type="simulation.roll_dice",
        expected_sequence=expected_sequence,
        payload={
            "expression": "1d20+5",
            "counter": "last_check",
            "reason": "v0.1 deterministic integration test",
            "target_id": "actor:target",
        },
    )


def test_identical_seed_and_command_produce_identical_event_and_state() -> None:
    first = SimulationEngine.create(
        campaign_id="campaign:test",
        session_id="session:test",
        seed=2026,
    )
    second = SimulationEngine.create(
        campaign_id="campaign:test",
        session_id="session:test",
        seed=2026,
    )

    first_events = first.handle(_roll_command())
    second_events = second.handle(_roll_command())

    assert [dumps_canonical(event_to_dict(event)) for event in first_events] == [
        dumps_canonical(event_to_dict(event)) for event in second_events
    ]
    assert dumps_canonical(state_to_dict(first.state)) == dumps_canonical(
        state_to_dict(second.state)
    )
    assert first.state.sequence == 1
    assert 6 <= first.state.counter("last_check") <= 25


def test_command_sequence_optimistic_concurrency_guard() -> None:
    engine = SimulationEngine.create(
        campaign_id="campaign:test",
        session_id="session:test",
        seed=1,
    )
    with pytest.raises(SequenceError):
        engine.handle(_roll_command(expected_sequence=2))


def test_unknown_command_is_rejected_without_mutating_state() -> None:
    engine = SimulationEngine.create(
        campaign_id="campaign:test",
        session_id="session:test",
        seed=1,
    )
    before = engine.state
    command = CommandEnvelope(
        command_id="command:unknown",
        campaign_id="campaign:test",
        session_id="session:test",
        command_type="not.real",
        expected_sequence=0,
    )
    with pytest.raises(UnsupportedCommandError):
        engine.handle(command)
    assert engine.state == before


def test_wrong_campaign_is_rejected() -> None:
    engine = SimulationEngine.create(
        campaign_id="campaign:test",
        session_id="session:test",
        seed=1,
    )
    command = CommandEnvelope(
        command_id="command:wrong-campaign",
        campaign_id="campaign:other",
        session_id="session:test",
        command_type="simulation.advance_tick",
        payload={"amount": 1},
    )
    with pytest.raises(ValidationError):
        engine.handle(command)
