# tests/test_world_bridge.py
from __future__ import annotations

from dataclasses import replace
from typing import Any

from godot_dnd_engine.character_creator import (
    CharacterCreatorRuntime,
    CharacterCreatorService,
    demo_character_catalog,
)
from godot_dnd_engine.client_bridge import PROTOCOL_NAME, PROTOCOL_VERSION
from godot_dnd_engine.engine import SimulationEngine
from godot_dnd_engine.world import WorldRuntime, demo_campaign
from godot_dnd_engine.world_bridge import WorldClientBridgeSession


def _request(
    kind: str,
    payload: dict[str, object],
    correlation: str = "world:test",
) -> dict[str, object]:
    return {
        "bridge_version": PROTOCOL_VERSION,
        "kind": kind,
        "request_id": f"request:{correlation}",
        "correlation_id": correlation,
        "generation": 0,
        "payload": payload,
    }


def _bridge() -> WorldClientBridgeSession:
    campaign_id = "campaign:world-bridge"
    return WorldClientBridgeSession(
        SimulationEngine.create(
            campaign_id=campaign_id,
            session_id="session:world-bridge",
            seed=41,
        ),
        None,
        CharacterCreatorService(CharacterCreatorRuntime(demo_character_catalog())),
        WorldRuntime(replace(demo_campaign(), campaign_id=campaign_id), seed=41),
    )


def _payload(response: dict[str, object] | None) -> dict[str, Any]:
    assert response is not None
    payload = response["payload"]
    assert isinstance(payload, dict)
    return payload


def test_world_bridge_advertises_playable_rpg_capabilities() -> None:
    bridge = _bridge()
    hello = bridge.handle_message(
        _request(
            "bridge.hello",
            {"protocol": PROTOCOL_NAME, "client": "godot", "capabilities": []},
        )
    )
    capabilities = _payload(hello)["capabilities"]
    assert "world.runtime.v1" in capabilities
    assert "dialogue.v1" in capabilities
    assert "quests.v1" in capabilities
    assert "shops.v1" in capabilities
    assert "characters.creator.v1" in capabilities


def test_world_snapshot_query_and_typed_command_flow_are_stream_isolated() -> None:
    bridge = _bridge()
    snapshot = bridge.handle_message(
        _request(
            "query.request",
            {"query_type": "world.snapshot", "query": {}},
            "world:snapshot",
        )
    )
    snapshot_payload = _payload(snapshot)
    assert "snapshot" not in snapshot_payload
    assert snapshot_payload["world_snapshot"]["state"]["mode"] == "world"

    command = {
        "command_id": "command:world-start",
        "campaign_id": "campaign:world-bridge",
        "session_id": "session:world-bridge",
        "command_type": "world.start",
        "payload": {"party_ids": ["actor:hero-a"]},
        "version": 1,
        "actor_id": None,
        "expected_sequence": 0,
    }
    response = bridge.handle_message(
        _request("command.submit", {"command": command}, "world:start")
    )
    payload = _payload(response)
    assert "snapshot" not in payload
    assert payload["world_snapshot"]["state"]["sequence"] == 1
    assert payload["world_events"][0]["type"] == "world.started"
    assert payload["presentation_events"][0]["type"] == "world.started"


def test_world_actions_include_engine_supplied_dialogue_descriptors() -> None:
    bridge = _bridge()
    result = bridge.handle_message(
        _request(
            "query.request",
            {"query_type": "world.actions", "query": {}},
            "world:actions",
        )
    )
    rows = _payload(result)["dialogues"]
    assert any(row["dialogue_id"] == "dialogue:warden-ilar" for row in rows)


def test_world_bridge_keeps_creator_and_world_sequences_independent() -> None:
    bridge = _bridge()
    world_command = {
        "command_id": "command:world-start",
        "campaign_id": "campaign:world-bridge",
        "session_id": "session:world-bridge",
        "command_type": "world.start",
        "payload": {"party_ids": ["actor:hero-a"]},
        "version": 1,
        "actor_id": None,
        "expected_sequence": 0,
    }
    world_response = bridge.handle_message(
        _request("command.submit", {"command": world_command}, "world:start")
    )
    assert _payload(world_response)["result"]["world_sequence"] == 1

    creator_schema = bridge.handle_message(
        _request(
            "query.request",
            {"query_type": "characters.creator.schema", "query": {}},
            "creator:schema",
        )
    )
    assert _payload(creator_schema)["catalog_id"] == "catalog:original-v0.9-demo"
