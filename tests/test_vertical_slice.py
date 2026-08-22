from __future__ import annotations

import pytest
from godot_dnd_engine.errors import SequenceError, ValidationError
from godot_dnd_engine.models import CommandEnvelope
from godot_dnd_engine.vertical_slice import TacticalVerticalSliceSession

CAMPAIGN_ID = "campaign:v07-test"
SESSION_ID = "session:v07-test"


def make_session(seed: int = 7) -> TacticalVerticalSliceSession:
    return TacticalVerticalSliceSession.create(
        campaign_id=CAMPAIGN_ID,
        session_id=SESSION_ID,
        seed=seed,
    )


def command(
    session: TacticalVerticalSliceSession,
    command_type: str,
    actor_id: str,
    payload: dict[str, object],
    *,
    sequence: int | None = None,
    ordinal: int = 1,
) -> CommandEnvelope:
    return CommandEnvelope(
        command_id=f"command:v07-test-{ordinal}",
        campaign_id=CAMPAIGN_ID,
        session_id=SESSION_ID,
        command_type=command_type,
        payload=payload,
        actor_id=actor_id,
        expected_sequence=session.sequence if sequence is None else sequence,
    )


def opposing_actor(session: TacticalVerticalSliceSession, actor_id: str) -> str:
    return next(
        combatant.actor_id
        for combatant in session.encounter.combatants
        if combatant.actor_id != actor_id
    )


def adjacent_destination(session: TacticalVerticalSliceSession, actor_id: str) -> dict[str, int]:
    if actor_id == "actor:ember":
        return {"x": 5, "y": 3}
    return {"x": 2, "y": 2}


def test_vertical_slice_snapshot_is_deterministic_and_client_shaped() -> None:
    first = make_session().snapshot()
    second = make_session().snapshot()
    assert first == second
    state = first["state"]
    assert isinstance(state, dict)
    assert state["sequence"] == 0
    assert state["mode"] == "tactical_vertical_slice"
    tactical = state["tactical"]
    assert isinstance(tactical, dict)
    assert tactical["display_name"] == "Sunken Courtyard"
    assert tactical["status"] == "active"
    assert {actor["actor_id"] for actor in tactical["actors"]} == {
        "actor:ember",
        "actor:shale",
    }
    assert tactical["space"]["width"] == 8
    assert tactical["space"]["height"] == 6


def test_spatial_queries_use_current_combat_movement_budget() -> None:
    session = make_session()
    actor_id = session.encounter.current_actor_id
    assert actor_id is not None
    result = session.query(
        "spatial.reachable",
        {"entity_id": actor_id, "movement_mode": "walk"},
    )
    assert result["cells"]
    destination = adjacent_destination(session, actor_id)
    path = session.preview(
        "spatial.path",
        {
            "entity_id": actor_id,
            "destination": destination,
            "movement_mode": "walk",
        },
    )
    assert path["legal"] is True
    assert int(path["cost_feet"]) <= session.encounter.combatant(
        actor_id
    ).economy.movement_remaining


def test_move_then_attack_preview_and_command_are_authoritative() -> None:
    session = make_session()
    actor_id = session.encounter.current_actor_id
    assert actor_id is not None
    target_id = opposing_actor(session, actor_id)

    initial_preview = session.preview(
        "tactical.attack",
        {"attacker_id": actor_id, "target_id": target_id},
    )
    assert initial_preview["legal"] is False
    assert initial_preview["distance_feet"] > 5

    destination = adjacent_destination(session, actor_id)
    moved = session.handle_command(
        command(
            session,
            "tactical.move",
            actor_id,
            {"destination": destination, "movement_mode": "walk"},
        )
    )
    assert session.sequence == 1
    assert session.spatial.placement(actor_id).anchor.x == destination["x"]
    assert session.spatial.placement(actor_id).anchor.y == destination["y"]
    assert moved.presentation_events[0]["type"] == "tactical.actor_moved"

    attack_preview = session.preview(
        "tactical.attack",
        {"attacker_id": actor_id, "target_id": target_id},
    )
    assert attack_preview["legal"] is True
    assert attack_preview["visible"] is True
    assert attack_preview["distance_feet"] <= 5

    before_hp = session.encounter.combatant(target_id).actor.hit_points.current
    attacked = session.handle_command(
        command(
            session,
            "tactical.attack",
            actor_id,
            {"target_id": target_id},
            ordinal=2,
        )
    )
    assert session.sequence == 2
    assert attacked.presentation_events[0]["type"] == "tactical.attack_resolved"
    assert session.encounter.combatant(actor_id).economy.action_available is False
    assert session.encounter.combatant(target_id).actor.hit_points.current <= before_hp
    assert attacked.snapshot["state"]["sequence"] == 2


def test_stale_sequence_and_wrong_turn_actor_fail_closed() -> None:
    session = make_session()
    current = session.encounter.current_actor_id
    assert current is not None
    other = opposing_actor(session, current)
    with pytest.raises(SequenceError):
        session.handle_command(
            command(
                session,
                "tactical.end_turn",
                current,
                {},
                sequence=99,
            )
        )
    with pytest.raises(ValidationError):
        session.handle_command(
            command(session, "tactical.end_turn", other, {}, ordinal=2)
        )
    assert session.sequence == 0


def test_end_turn_advances_authoritative_current_actor() -> None:
    session = make_session()
    current = session.encounter.current_actor_id
    assert current is not None
    result = session.handle_command(
        command(session, "tactical.end_turn", current, {})
    )
    assert session.sequence == 1
    assert session.encounter.current_actor_id != current
    assert result.presentation_events == (
        {
            "type": "tactical.turn_started",
            "actor_id": session.encounter.current_actor_id,
            "payload": {
                "round_number": session.encounter.round_number,
                "turn_index": session.encounter.turn_index,
            },
            "sequence": 1,
        },
    )


def test_complete_encounter_can_be_played_through_typed_commands() -> None:
    session = make_session(seed=11)
    current = session.encounter.current_actor_id
    assert current is not None
    target = opposing_actor(session, current)
    destination = adjacent_destination(session, current)
    session.handle_command(
        command(
            session,
            "tactical.move",
            current,
            {"destination": destination, "movement_mode": "walk"},
        )
    )

    ordinal = 2
    for _ in range(30):
        if session.encounter.status.value == "ended":
            break
        current = session.encounter.current_actor_id
        assert current is not None
        target = opposing_actor(session, current)
        if session.encounter.combatant(target).life_state.value != "dead":
            preview = session.preview(
                "tactical.attack",
                {"attacker_id": current, "target_id": target},
            )
            assert preview["legal"] is True
            session.handle_command(
                command(
                    session,
                    "tactical.attack",
                    current,
                    {"target_id": target},
                    ordinal=ordinal,
                )
            )
            ordinal += 1
        if session.encounter.status.value == "ended":
            break
        session.handle_command(
            command(
                session,
                "tactical.end_turn",
                current,
                {},
                ordinal=ordinal,
            )
        )
        ordinal += 1

    assert session.encounter.status.value == "ended"
    living = [
        combatant
        for combatant in session.encounter.combatants
        if combatant.life_state.value != "dead"
    ]
    assert len(living) == 1
    assert session.recent_events[-1]["type"] == "tactical.encounter_ended"


def test_malformed_tactical_payloads_are_rejected() -> None:
    session = make_session()
    current = session.encounter.current_actor_id
    assert current is not None
    with pytest.raises(ValidationError):
        session.handle_command(
            command(
                session,
                "tactical.move",
                current,
                {"destination": {"x": "bad", "y": 2}},
            )
        )
    with pytest.raises(ValidationError):
        session.preview(
            "tactical.attack",
            {"attacker_id": current, "target_id": ""},
        )
