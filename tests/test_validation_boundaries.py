# tests/test_validation_boundaries.py
from __future__ import annotations

import pytest

from godot_dnd_engine.dice import DiceExpression, roll_expression
from godot_dnd_engine.engine import SimulationEngine
from godot_dnd_engine.errors import SequenceError, ValidationError
from godot_dnd_engine.models import CommandEnvelope, EventEnvelope, GameState
from godot_dnd_engine.reducer import apply_event
from godot_dnd_engine.rng import DeterministicRNG
from godot_dnd_engine.serialization import event_from_dict, state_from_dict


@pytest.mark.parametrize(
    "kwargs",
    [
        {"count": True, "sides": 6},
        {"count": 1, "sides": True},
        {"count": 1, "sides": 6, "modifier": True},
        {"count": 0, "sides": 6},
        {"count": 1, "sides": 1},
        {"count": 1, "sides": 6, "modifier": 1_000_001},
    ],
)
def test_dice_expression_constructor_validation(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        DiceExpression(**kwargs)  # type: ignore[arg-type]


def test_dice_parser_rejects_non_string_and_empty_reason() -> None:
    with pytest.raises(ValidationError):
        DiceExpression.parse(3)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        roll_expression(
            DiceExpression(1, 6),
            DeterministicRNG.from_seed(1),
            reason=" ",
        )


@pytest.mark.parametrize("seed", [True, 1.5])
def test_rng_rejects_non_integer_seed(seed: object) -> None:
    with pytest.raises(ValidationError):
        DeterministicRNG.from_seed(seed)  # type: ignore[arg-type]


def test_rng_rejects_invalid_stream_and_die() -> None:
    with pytest.raises(ValidationError):
        DeterministicRNG.from_seed(1, stream=True)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        DeterministicRNG.from_seed(1).roll_die(1)
    with pytest.raises(ValidationError):
        DeterministicRNG.restore((1 << 64, 1))
    with pytest.raises(ValidationError):
        DeterministicRNG.restore((1,))  # type: ignore[arg-type]


def test_randbelow_supports_full_uint32_range() -> None:
    value = DeterministicRNG.from_seed(9).randbelow(1 << 32)
    assert 0 <= value < 1 << 32


def test_command_and_event_envelope_validation() -> None:
    with pytest.raises(ValidationError):
        CommandEnvelope(
            command_id="command:x",
            campaign_id="campaign:x",
            session_id="session:x",
            command_type="",
        )
    with pytest.raises(ValidationError):
        CommandEnvelope(
            command_id="command:x",
            campaign_id="campaign:x",
            session_id="session:x",
            command_type="x",
            version=True,
        )
    with pytest.raises(ValidationError):
        CommandEnvelope(
            command_id="command:x",
            campaign_id="campaign:x",
            session_id="session:x",
            command_type="x",
            expected_sequence=-1,
        )
    with pytest.raises(ValidationError):
        CommandEnvelope(
            command_id="command:x",
            campaign_id="campaign:x",
            session_id="session:x",
            command_type="x",
            payload=3,  # type: ignore[arg-type]
        )
    with pytest.raises(ValidationError):
        EventEnvelope(
            event_id="event:x",
            campaign_id="campaign:x",
            session_id="session:x",
            sequence=0,
            event_type="x",
            correlation_id="command:x",
            causation_id="command:x",
        )
    with pytest.raises(ValidationError):
        EventEnvelope(
            event_id="event:x",
            campaign_id="campaign:x",
            session_id="session:x",
            sequence=1,
            event_type="",
            correlation_id="command:x",
            causation_id="command:x",
        )
    with pytest.raises(ValidationError):
        EventEnvelope(
            event_id="event:x",
            campaign_id="campaign:x",
            session_id="session:x",
            sequence=1,
            event_type="x",
            correlation_id="command:x",
            causation_id="command:x",
            tick=-1,
        )


def test_game_state_validation_and_counter_default() -> None:
    state = GameState(campaign_id="campaign:x", session_id="session:x")
    assert state.counter("missing", 7) == 7
    with pytest.raises(ValidationError):
        GameState(campaign_id="campaign:x", session_id="session:x", sequence=-1)
    with pytest.raises(ValidationError):
        GameState(campaign_id="campaign:x", session_id="session:x", tick=-1)
    with pytest.raises(ValidationError):
        GameState(
            campaign_id="campaign:x",
            session_id="session:x",
            counters=(("x", 1), ("x", 2)),
        )
    with pytest.raises(ValidationError):
        GameState(
            campaign_id="campaign:x",
            session_id="session:x",
            counters=(("", 1),),
        )
    with pytest.raises(ValidationError):
        GameState(
            campaign_id="campaign:x",
            session_id="session:x",
            counters=(("x", True),),
        )


def _event(
    *,
    sequence: int = 1,
    event_type: str = "simulation.tick_advanced",
    tick: int = 1,
    payload: dict[str, object] | None = None,
) -> EventEnvelope:
    return EventEnvelope(
        event_id=f"event:{sequence}",
        campaign_id="campaign:x",
        session_id="session:x",
        sequence=sequence,
        event_type=event_type,
        correlation_id="command:x",
        causation_id="command:x",
        tick=tick,
        payload=payload or {},
    )


def test_reducer_rejects_identity_sequence_tick_and_unknown_event_errors() -> None:
    state = GameState(campaign_id="campaign:x", session_id="session:x")
    wrong_identity = EventEnvelope(
        event_id="event:1",
        campaign_id="campaign:other",
        session_id="session:x",
        sequence=1,
        event_type="simulation.tick_advanced",
        correlation_id="command:x",
        causation_id="command:x",
        tick=1,
    )
    with pytest.raises(ValidationError):
        apply_event(state, wrong_identity)
    with pytest.raises(SequenceError):
        apply_event(state, _event(sequence=2))
    state_at_tick = GameState(campaign_id="campaign:x", session_id="session:x", tick=4)
    with pytest.raises(SequenceError):
        apply_event(state_at_tick, _event(tick=3))
    with pytest.raises(ValidationError):
        apply_event(state, _event(event_type="unknown"))
    with pytest.raises(ValidationError):
        apply_event(
            state,
            _event(event_type="dice.rolled", payload={"counter": "x", "total": True}),
        )
    with pytest.raises(ValidationError):
        apply_event(
            state,
            _event(event_type="dice.rolled", payload={"counter": "", "total": 1}),
        )


def test_engine_validates_session_roll_fields_and_tick_amount() -> None:
    engine = SimulationEngine.create(
        campaign_id="campaign:x",
        session_id="session:x",
        seed=1,
    )
    bad_session = CommandEnvelope(
        command_id="command:bad-session",
        campaign_id="campaign:x",
        session_id="session:other",
        command_type="simulation.advance_tick",
    )
    with pytest.raises(ValidationError):
        engine.handle(bad_session)

    def command(payload: dict[str, object]) -> CommandEnvelope:
        return CommandEnvelope(
            command_id="command:roll",
            campaign_id="campaign:x",
            session_id="session:x",
            command_type="simulation.roll_dice",
            payload=payload,
        )

    for payload in (
        {},
        {"expression": "1d20", "counter": ""},
        {"expression": "1d20", "reason": ""},
        {"expression": "1d20", "target_id": 1},
        {"expression": "1d20", "target_id": "campaign:not-actor"},
    ):
        with pytest.raises(ValidationError):
            engine.handle(command(payload))

    with pytest.raises(ValidationError):
        engine.handle(
            CommandEnvelope(
                command_id="command:tick",
                campaign_id="campaign:x",
                session_id="session:x",
                command_type="simulation.advance_tick",
                payload={"amount": 0},
            )
        )


def test_serialization_rejects_invalid_event_and_snapshot_shapes() -> None:
    with pytest.raises(ValidationError):
        state_from_dict([])  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        state_from_dict(
            {
                "schema_version": 1,
                "campaign_id": "campaign:x",
                "session_id": "session:x",
                "sequence": 0,
                "tick": 0,
                "counters": [],
            }
        )
    with pytest.raises(ValidationError):
        event_from_dict({})
    with pytest.raises(ValidationError):
        event_from_dict(
            {
                "schema_version": 2,
                "event_id": "event:1",
                "campaign_id": "campaign:x",
                "session_id": "session:x",
                "sequence": 1,
                "event_type": "x",
                "version": 1,
                "tick": 0,
                "correlation_id": "command:x",
                "causation_id": "command:x",
                "payload": {},
            }
        )
    with pytest.raises(ValidationError):
        event_from_dict(
            {
                "schema_version": 1,
                "event_id": "event:1",
                "campaign_id": "campaign:x",
                "session_id": "session:x",
                "sequence": 1,
                "event_type": "x",
                "version": 1,
                "tick": 0,
                "correlation_id": "command:x",
                "causation_id": "command:x",
                "payload": [],
            }
        )
