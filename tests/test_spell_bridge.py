# tests/test_spell_bridge.py
from __future__ import annotations

from typing import Any

from godot_dnd_engine.client_bridge import PROTOCOL_NAME, PROTOCOL_VERSION
from godot_dnd_engine.engine import SimulationEngine
from godot_dnd_engine.spell_bridge import SpellClientBridgeSession
from godot_dnd_engine.spell_slice import SpellEnabledTacticalSession


def _request(
    kind: str,
    payload: dict[str, object],
    *,
    request_id: str = "client-request:spell",
    correlation_id: str = "interaction:spell",
    generation: int = 1,
) -> dict[str, object]:
    return {
        "bridge_version": PROTOCOL_VERSION,
        "kind": kind,
        "request_id": request_id,
        "correlation_id": correlation_id,
        "generation": generation,
        "payload": payload,
    }


def _session() -> SpellClientBridgeSession:
    campaign_id = "campaign:spell-bridge"
    session_id = "session:spell-bridge"
    return SpellClientBridgeSession(
        SimulationEngine.create(campaign_id=campaign_id, session_id=session_id, seed=19),
        SpellEnabledTacticalSession.create(
            campaign_id=campaign_id,
            session_id=session_id,
            seed=19,
        ),
    )


def _payload(response: dict[str, object] | None) -> dict[str, Any]:
    assert response is not None
    payload = response["payload"]
    assert isinstance(payload, dict)
    return payload


def test_spell_bridge_negotiates_additive_capabilities_and_augmented_snapshot() -> None:
    bridge = _session()
    hello = bridge.handle_message(
        _request(
            "bridge.hello",
            {"protocol": PROTOCOL_NAME, "client": "godot", "capabilities": []},
        )
    )
    hello_payload = _payload(hello)
    capabilities = hello_payload["capabilities"]
    assert "tactical.vertical-slice.v1" in capabilities
    assert "spells.runtime.v1" in capabilities
    assert "spells.previews.v1" in capabilities

    snapshot = bridge.handle_message(
        _request(
            "query.request",
            {"query_type": "tactical.snapshot", "query": {}},
            request_id="client-request:snapshot",
        )
    )
    state = _payload(snapshot)["snapshot"]["state"]
    assert state["mode"] == "tactical_vertical_slice"
    assert state["tactical"]["spellcasting"]["casters"]


def test_spell_available_and_preview_queries_delegate_to_authority() -> None:
    bridge = _session()
    assert bridge.spell_tactical is not None
    caster = bridge.spell_tactical.encounter.current_actor_id
    assert caster is not None
    target = next(
        row.actor.actor_id
        for row in bridge.spell_tactical.encounter.combatants
        if row.actor.actor_id != caster
    )

    available = bridge.handle_message(
        _request(
            "query.request",
            {"query_type": "spells.available", "query": {"actor_id": caster}},
        )
    )
    spells = _payload(available)["spells"]
    assert any(item["spell_id"] == "spell:arc-lance" for item in spells)

    preview = bridge.handle_message(
        _request(
            "preview.request",
            {
                "preview_type": "spells.preview",
                "preview": {
                    "caster_id": caster,
                    "spell_id": "spell:arc-lance",
                    "slot_level": 0,
                    "target_ids": [target],
                },
            },
            request_id="client-request:preview",
            generation=2,
        )
    )
    preview_payload = _payload(preview)
    assert preview_payload["legal"] is True
    assert preview_payload["target_ids"] == [target]


def test_typed_spell_command_returns_authoritative_snapshot_and_presentation_event() -> None:
    bridge = _session()
    assert bridge.spell_tactical is not None
    tactical = bridge.spell_tactical
    caster = tactical.encounter.current_actor_id
    assert caster is not None
    target = next(
        row.actor.actor_id
        for row in tactical.encounter.combatants
        if row.actor.actor_id != caster
    )
    command = {
        "command_id": "command:spell-bridge-cast",
        "campaign_id": "campaign:spell-bridge",
        "session_id": "session:spell-bridge",
        "command_type": "tactical.cast_spell",
        "payload": {
            "spell_id": "spell:arc-lance",
            "slot_level": 0,
            "target_ids": [target],
        },
        "version": 1,
        "actor_id": caster,
        "expected_sequence": tactical.sequence,
    }
    response = bridge.handle_message(
        _request(
            "command.submit",
            {"command": command},
            request_id="client-request:cast",
            generation=3,
        )
    )
    payload = _payload(response)
    assert payload["snapshot"]["state"]["sequence"] == 1
    assert payload["presentation_events"][0]["type"] == "tactical.spell_resolved"
    assert payload["result"]["spell_id"] == "spell:arc-lance"


def test_spell_bridge_rejects_non_tactical_core_commands_while_provider_is_active() -> None:
    bridge = _session()
    response = bridge.handle_message(
        _request(
            "command.submit",
            {
                "command": {
                    "command_id": "command:no-second-stream",
                    "campaign_id": "campaign:spell-bridge",
                    "session_id": "session:spell-bridge",
                    "command_type": "simulation.advance_tick",
                    "payload": {"amount": 1},
                    "version": 1,
                    "actor_id": None,
                    "expected_sequence": 0,
                }
            },
        )
    )
    assert response is not None
    assert response["kind"] == "command.rejected"
    assert response["error"]["category"] == "unsupported"
