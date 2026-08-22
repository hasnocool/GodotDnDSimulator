from __future__ import annotations

from godot_dnd_engine.client_bridge import (
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    ClientBridgeSession,
)
from godot_dnd_engine.engine import SimulationEngine
from godot_dnd_engine.vertical_slice import TacticalVerticalSliceSession

CAMPAIGN_ID = "campaign:v07-bridge"
SESSION_ID = "session:v07-bridge"


def bridge_session() -> ClientBridgeSession:
    engine = SimulationEngine.create(
        campaign_id=CAMPAIGN_ID,
        session_id=SESSION_ID,
        seed=7,
    )
    tactical = TacticalVerticalSliceSession.create(
        campaign_id=CAMPAIGN_ID,
        session_id=SESSION_ID,
        seed=7,
    )
    return ClientBridgeSession(engine, tactical=tactical)


def message(
    kind: str,
    payload: dict[str, object],
    *,
    request_id: str = "request:v07",
    correlation_id: str = "correlation:v07",
    generation: int = 0,
) -> dict[str, object]:
    return {
        "bridge_version": PROTOCOL_VERSION,
        "kind": kind,
        "request_id": request_id,
        "correlation_id": correlation_id,
        "generation": generation,
        "payload": payload,
    }


def command_payload(
    session: ClientBridgeSession,
    command_type: str,
    actor_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    assert session.tactical is not None
    return {
        "command": {
            "command_id": "command:v07-bridge-1",
            "campaign_id": CAMPAIGN_ID,
            "session_id": SESSION_ID,
            "command_type": command_type,
            "payload": payload,
            "version": 1,
            "actor_id": actor_id,
            "expected_sequence": session.tactical.sequence,
        }
    }


def test_hello_advertises_tactical_and_spatial_capabilities() -> None:
    session = bridge_session()
    response = session.handle_message(
        message("bridge.hello", {"protocol": PROTOCOL_NAME})
    )
    assert response is not None and response["ok"] is True
    capabilities = response["payload"]["capabilities"]
    assert "tactical.vertical-slice.v1" in capabilities
    assert "spatial.previews.v1" in capabilities


def test_tactical_snapshot_query_returns_composite_authoritative_state() -> None:
    session = bridge_session()
    response = session.handle_message(
        message(
            "query.request",
            {"query_type": "tactical.snapshot", "query": {}},
        )
    )
    assert response is not None and response["kind"] == "query.result"
    snapshot = response["payload"]["snapshot"]
    assert snapshot["state"]["mode"] == "tactical_vertical_slice"
    assert snapshot["state"]["sequence"] == 0


def test_spatial_preview_is_delegated_to_authoritative_slice() -> None:
    session = bridge_session()
    assert session.tactical is not None
    actor_id = session.tactical.encounter.current_actor_id
    assert actor_id is not None
    destination = {"x": 5, "y": 3} if actor_id == "actor:ember" else {"x": 2, "y": 2}
    response = session.handle_message(
        message(
            "preview.request",
            {
                "preview_type": "spatial.path",
                "preview": {
                    "entity_id": actor_id,
                    "destination": destination,
                    "movement_mode": "walk",
                },
            },
        )
    )
    assert response is not None and response["kind"] == "preview.result"
    assert response["payload"]["legal"] is True
    assert response["payload"]["cost_feet"] > 0


def test_tactical_command_returns_snapshot_and_presentation_events() -> None:
    session = bridge_session()
    assert session.tactical is not None
    actor_id = session.tactical.encounter.current_actor_id
    assert actor_id is not None
    destination = {"x": 5, "y": 3} if actor_id == "actor:ember" else {"x": 2, "y": 2}
    response = session.handle_message(
        message(
            "command.submit",
            command_payload(
                session,
                "tactical.move",
                actor_id,
                {"destination": destination, "movement_mode": "walk"},
            ),
        )
    )
    assert response is not None and response["kind"] == "command.accepted"
    assert response["payload"]["snapshot"]["state"]["sequence"] == 1
    assert response["payload"]["presentation_events"][0]["type"] == "tactical.actor_moved"
    assert "events" not in response["payload"]


def test_core_only_bridge_still_rejects_unregistered_previews() -> None:
    engine = SimulationEngine.create(
        campaign_id=CAMPAIGN_ID,
        session_id=SESSION_ID,
        seed=7,
    )
    session = ClientBridgeSession(engine)
    response = session.handle_message(
        message(
            "preview.request",
            {"preview_type": "spatial.path", "preview": {}},
        )
    )
    assert response is not None and response["ok"] is False
    assert response["kind"] == "preview.rejected"
