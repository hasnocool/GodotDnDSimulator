# tests/test_character_bridge.py
from __future__ import annotations

from typing import Any

from godot_dnd_engine.character_bridge import CharacterClientBridgeSession
from godot_dnd_engine.character_creator import (
    CharacterCreatorRuntime,
    CharacterCreatorService,
    demo_character_catalog,
)
from godot_dnd_engine.client_bridge import PROTOCOL_NAME, PROTOCOL_VERSION
from godot_dnd_engine.engine import SimulationEngine


def _request(kind: str, payload: dict[str, object], correlation: str = "creator:test") -> dict[str, object]:
    return {
        "bridge_version": PROTOCOL_VERSION,
        "kind": kind,
        "request_id": f"request:{correlation}",
        "correlation_id": correlation,
        "generation": 0,
        "payload": payload,
    }


def _bridge() -> CharacterClientBridgeSession:
    return CharacterClientBridgeSession(
        SimulationEngine.create(
            campaign_id="campaign:creator",
            session_id="session:creator",
            seed=23,
        ),
        None,
        CharacterCreatorService(CharacterCreatorRuntime(demo_character_catalog())),
    )


def _payload(response: dict[str, object] | None) -> dict[str, Any]:
    assert response is not None
    payload = response["payload"]
    assert isinstance(payload, dict)
    return payload


def _draft_payload() -> dict[str, object]:
    return {
        "actor_id": "actor:bridge-created",
        "name": "Mira Quill",
        "selected_choice_ids": [
            "species:stonekin",
            "background:wayfarer",
            "class:guardian",
            "skill:athletics",
            "skill:perception",
            "equipment:defender-kit",
            "featurechoice:interpose",
        ],
        "ability_method_id": "standard-array",
        "ability_scores": {
            "strength": 15,
            "dexterity": 12,
            "constitution": 14,
            "intelligence": 8,
            "wisdom": 13,
            "charisma": 10,
        },
        "appearance": {"portrait": "portrait:mira", "hair": "silver"},
        "biography": "A patient road warden.",
        "personality": "Protective and observant.",
    }


def test_character_bridge_advertises_creator_and_returns_engine_schema() -> None:
    bridge = _bridge()
    hello = bridge.handle_message(
        _request(
            "bridge.hello",
            {"protocol": PROTOCOL_NAME, "client": "godot", "capabilities": []},
        )
    )
    capabilities = _payload(hello)["capabilities"]
    assert "characters.creator.v1" in capabilities
    assert "characters.levelup.v1" in capabilities

    schema = bridge.handle_message(
        _request(
            "query.request",
            {"query_type": "characters.creator.schema", "query": {}},
            "creator:schema",
        )
    )
    result = _payload(schema)
    assert result["catalog_id"] == "catalog:original-v0.9-demo"
    assert "species" in result["steps"]
    assert result["choices"]


def test_character_create_and_level_up_flow_through_typed_bridge_commands() -> None:
    bridge = _bridge()
    create_command = {
        "command_id": "command:create-character",
        "campaign_id": "campaign:creator",
        "session_id": "session:creator",
        "command_type": "characters.create",
        "payload": _draft_payload(),
        "version": 1,
        "actor_id": "actor:bridge-created",
        "expected_sequence": 0,
    }
    created = bridge.handle_message(
        _request("command.submit", {"command": create_command}, "creator:create")
    )
    record = _payload(created)["result"]["record"]
    assert record["actor"]["name"] == "Mira Quill"
    assert record["class_id"] == "class:guardian"

    choices = bridge.handle_message(
        _request(
            "query.request",
            {
                "query_type": "characters.levelup.choices",
                "query": {"actor_id": "actor:bridge-created"},
            },
            "creator:levelup-choices",
        )
    )
    choice_rows = _payload(choices)["choices"]
    assert [item["choice_id"] for item in choice_rows] == ["advance:guardian-brace"]

    level_command = {
        "command_id": "command:level-character",
        "campaign_id": "campaign:creator",
        "session_id": "session:creator",
        "command_type": "characters.level_up",
        "payload": {
            "actor_id": "actor:bridge-created",
            "selected_choice_ids": ["advance:guardian-brace"],
        },
        "version": 1,
        "actor_id": "actor:bridge-created",
        "expected_sequence": 0,
    }
    advanced = bridge.handle_message(
        _request("command.submit", {"command": level_command}, "creator:levelup")
    )
    advanced_record = _payload(advanced)["result"]["record"]
    assert advanced_record["actor"]["level"] == 2
    assert "feature:brace-training" in advanced_record["feature_ids"]
