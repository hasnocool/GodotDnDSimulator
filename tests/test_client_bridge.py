from __future__ import annotations

import asyncio
import json

import pytest
from godot_dnd_engine.client_bridge import (
    CAPABILITIES,
    MAX_MESSAGE_BYTES,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    BridgeProtocolError,
    ClientBridgeServer,
    ClientBridgeSession,
)
from godot_dnd_engine.engine import SimulationEngine


def request(
    kind: str,
    *,
    request_id: str = "client-request:test",
    correlation_id: str = "interaction:test",
    generation: int = 0,
    payload: dict[str, object] | None = None,
    bridge_version: int = PROTOCOL_VERSION,
) -> dict[str, object]:
    return {
        "bridge_version": bridge_version,
        "kind": kind,
        "request_id": request_id,
        "correlation_id": correlation_id,
        "generation": generation,
        "payload": {} if payload is None else payload,
    }


def command_payload(
    command_id: str,
    *,
    command_type: str = "simulation.advance_tick",
    expected_sequence: int | None = 0,
) -> dict[str, object]:
    return {
        "command": {
            "command_id": command_id,
            "campaign_id": "campaign:bridge-test",
            "session_id": "session:bridge-test",
            "command_type": command_type,
            "payload": {"amount": 1},
            "version": 1,
            "actor_id": None,
            "expected_sequence": expected_sequence,
        }
    }


def session() -> ClientBridgeSession:
    return ClientBridgeSession(
        SimulationEngine.create(
            campaign_id="campaign:bridge-test",
            session_id="session:bridge-test",
            seed=0,
        )
    )


def test_hello_negotiates_protocol_and_capabilities() -> None:
    bridge = session()
    response = bridge.handle_message(
        request(
            "bridge.hello",
            payload={"protocol": PROTOCOL_NAME, "client": "godot", "capabilities": []},
        )
    )
    assert response is not None
    assert response["kind"] == "bridge.hello.accepted"
    assert response["ok"] is True
    assert "error" not in response
    assert response["payload"] == {
        "protocol": PROTOCOL_NAME,
        "capabilities": list(CAPABILITIES),
    }


def test_hello_rejects_wrong_protocol_and_version() -> None:
    bridge = session()
    wrong_protocol = bridge.handle_message(
        request("bridge.hello", payload={"protocol": "other"})
    )
    assert wrong_protocol is not None
    assert wrong_protocol["kind"] == "bridge.hello.rejected"
    assert wrong_protocol["error"]["category"] == "incompatible_version"

    wrong_version = bridge.handle_message(
        request(
            "bridge.hello",
            bridge_version=PROTOCOL_VERSION + 1,
            payload={"protocol": PROTOCOL_NAME},
        )
    )
    assert wrong_version is not None
    assert wrong_version["kind"] == "bridge.hello.rejected"
    assert wrong_version["error"]["category"] == "incompatible_version"


def test_command_accepts_ordered_events() -> None:
    bridge = session()
    response = bridge.handle_message(
        request(
            "command.submit",
            payload=command_payload("command:bridge-1"),
        )
    )
    assert response is not None
    assert response["kind"] == "command.accepted"
    assert response["ok"] is True
    payload = response["payload"]
    assert list(payload) == ["events"]
    assert payload["events"][0]["sequence"] == 1
    assert len(bridge.events) == 1


def test_command_conflict_unsupported_and_validation_are_categorized() -> None:
    bridge = session()
    accepted = bridge.handle_message(
        request("command.submit", payload=command_payload("command:first"))
    )
    assert accepted is not None and accepted["ok"] is True

    conflict = bridge.handle_message(
        request("command.submit", payload=command_payload("command:stale"))
    )
    assert conflict is not None
    assert conflict["error"]["category"] == "conflict"

    unsupported_payload = command_payload(
        "command:unsupported",
        command_type="simulation.not_real",
        expected_sequence=1,
    )
    unsupported = bridge.handle_message(
        request("command.submit", payload=unsupported_payload)
    )
    assert unsupported is not None
    assert unsupported["error"]["category"] == "unsupported"

    malformed = bridge.handle_message(
        request("command.submit", payload={"command": {"command_id": "command:x"}})
    )
    assert malformed is not None
    assert malformed["error"]["category"] == "validation"


def test_queries_return_snapshot_capabilities_and_explicit_unsupported() -> None:
    bridge = session()
    capabilities = bridge.handle_message(
        request(
            "query.request",
            payload={"query_type": "bridge.capabilities", "query": {}},
        )
    )
    assert capabilities is not None
    assert capabilities["kind"] == "query.result"
    assert capabilities["payload"]["capabilities"] == list(CAPABILITIES)

    snapshot = bridge.handle_message(
        request(
            "query.request",
            payload={"query_type": "bridge.snapshot", "query": {}},
        )
    )
    assert snapshot is not None
    assert snapshot["payload"]["snapshot"]["state"]["sequence"] == 0

    resync = bridge.handle_message(
        request(
            "query.request",
            payload={"query_type": "bridge.resync", "query": {"after_sequence": 0}},
        )
    )
    assert resync is not None
    assert resync["payload"]["snapshot"]["state"]["sequence"] == 0

    unsupported = bridge.handle_message(
        request(
            "query.request",
            payload={"query_type": "actor.inspect", "query": {}},
        )
    )
    assert unsupported is not None
    assert unsupported["kind"] == "query.rejected"
    assert unsupported["error"]["category"] == "unsupported"


def test_query_and_envelope_validation_fail_closed() -> None:
    bridge = session()
    invalid_after = bridge.handle_message(
        request(
            "query.request",
            payload={"query_type": "bridge.resync", "query": {"after_sequence": -1}},
        )
    )
    assert invalid_after is not None
    assert invalid_after["error"]["category"] == "validation"

    missing_query_type = bridge.handle_message(
        request("query.request", payload={"query": {}})
    )
    assert missing_query_type is not None
    assert missing_query_type["error"]["category"] == "validation"

    with pytest.raises(BridgeProtocolError):
        bridge.handle_message({"kind": "bridge.hello"})
    with pytest.raises(BridgeProtocolError):
        bridge.handle_message(
            request("bridge.hello", generation=-1, payload={"protocol": PROTOCOL_NAME})
        )


def test_preview_cancel_and_unknown_request_behavior() -> None:
    bridge = session()
    preview = bridge.handle_message(
        request(
            "preview.request",
            generation=3,
            payload={"preview_type": "movement.path", "preview": {}},
        )
    )
    assert preview is not None
    assert preview["kind"] == "preview.rejected"
    assert preview["error"]["category"] == "unsupported"

    cancelled = bridge.handle_message(
        request("request.cancel", payload={"target_request_id": "client-request:old"})
    )
    assert cancelled is None

    unknown = bridge.handle_message(request("mystery.request"))
    assert unknown is not None
    assert unknown["kind"] == "request.rejected"
    assert unknown["error"]["category"] == "unsupported"


def test_server_line_parser_returns_validation_response_for_bad_input() -> None:
    server = ClientBridgeServer(session())
    malformed = server._handle_line(b"not json\n")
    assert malformed is not None
    assert malformed["kind"] == "request.rejected"
    assert malformed["error"]["category"] == "validation"

    non_object = server._handle_line(b"[]\n")
    assert non_object is not None
    assert non_object["error"]["category"] == "validation"

    oversized = server._handle_line(b"x" * (MAX_MESSAGE_BYTES + 1))
    assert oversized is not None
    assert oversized["error"]["category"] == "validation"
    assert "exceeded" in oversized["error"]["debug_detail"]


@pytest.mark.asyncio
async def test_async_tcp_round_trip_uses_newline_delimited_json() -> None:
    bridge = ClientBridgeServer(session())
    server = await asyncio.start_server(bridge.handle_client, "127.0.0.1", 0)
    sockets = server.sockets
    assert sockets
    port = sockets[0].getsockname()[1]

    async with server:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        message = request(
            "bridge.hello",
            payload={"protocol": PROTOCOL_NAME, "client": "godot", "capabilities": []},
        )
        writer.write(
            (json.dumps(message, sort_keys=True, separators=(",", ":")) + "\n").encode()
        )
        await writer.drain()
        response = json.loads((await reader.readline()).decode())
        assert response["kind"] == "bridge.hello.accepted"
        assert response["bridge_version"] == PROTOCOL_VERSION
        assert "error" not in response

        writer.close()
        await writer.wait_closed()
