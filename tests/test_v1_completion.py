from __future__ import annotations

from dataclasses import replace
from typing import Any

from godot_dnd_engine.character_creator import (
    CharacterCreatorRuntime,
    CharacterCreatorService,
    demo_character_catalog,
)
from godot_dnd_engine.client_bridge import PROTOCOL_VERSION
from godot_dnd_engine.engine import SimulationEngine
from godot_dnd_engine.spell_slice import SpellEnabledTacticalSession
from godot_dnd_engine.world import WorldRuntime, demo_campaign, restore_world_runtime
from godot_dnd_engine.world_bridge import WorldClientBridgeSession


def _request(
    kind: str,
    payload: dict[str, object],
    correlation: str,
) -> dict[str, object]:
    return {
        "bridge_version": PROTOCOL_VERSION,
        "kind": kind,
        "request_id": f"request:{correlation}",
        "correlation_id": correlation,
        "generation": 0,
        "payload": payload,
    }


def _payload(response: dict[str, object] | None) -> dict[str, Any]:
    assert response is not None
    payload = response["payload"]
    assert isinstance(payload, dict)
    return payload


def _bridge() -> WorldClientBridgeSession:
    campaign_id = "campaign:v1-completion"
    return WorldClientBridgeSession(
        SimulationEngine.create(
            campaign_id=campaign_id,
            session_id="session:v1-completion",
            seed=73,
        ),
        None,
        CharacterCreatorService(CharacterCreatorRuntime(demo_character_catalog())),
        WorldRuntime(replace(demo_campaign(), campaign_id=campaign_id), seed=73),
    )


def _command(
    bridge: WorldClientBridgeSession,
    command_type: str,
    payload: dict[str, object],
    correlation: str,
) -> dict[str, object] | None:
    return bridge.handle_message(
        _request(
            "command.submit",
            {
                "command": {
                    "command_id": f"command:{correlation}",
                    "campaign_id": "campaign:v1-completion",
                    "session_id": "session:v1-completion",
                    "command_type": command_type,
                    "payload": payload,
                    "version": 1,
                    "actor_id": None,
                    "expected_sequence": bridge.world.state.sequence,
                }
            },
            correlation,
        )
    )


def _runtime_command(
    runtime: WorldRuntime,
    command_type: str,
    payload: dict[str, object],
) -> None:
    runtime.handle_command(
        command_type,
        payload,
        expected_sequence=runtime.state.sequence,
    )


def _advance_to_road_encounter(bridge: WorldClientBridgeSession) -> None:
    _command(
        bridge,
        "world.start",
        {"party_ids": ["actor:hero-a"]},
        "road-start",
    )
    _command(
        bridge,
        "dialogue.start",
        {"dialogue_id": "dialogue:warden-ilar"},
        "road-dialogue",
    )
    _command(
        bridge,
        "dialogue.choose",
        {"choice_id": "choice:accept-quarry"},
        "road-accept",
    )
    _command(
        bridge,
        "dialogue.choose",
        {"choice_id": "choice:leave-warden"},
        "road-leave",
    )
    _command(
        bridge,
        "world.travel",
        {"area_id": "area:old-road"},
        "road-travel",
    )


def test_v1_campaign_content_meets_playable_rpg_scope() -> None:
    campaign = demo_campaign()
    area_tags = {tag for area in campaign.areas for tag in area.tags}
    regular_encounters = [item for item in campaign.encounters if not item.boss]
    boss_encounters = [item for item in campaign.encounters if item.boss]

    assert "village" in area_tags
    assert "dungeon" in area_tags
    assert len(regular_encounters) >= 3
    assert len(boss_encounters) >= 1
    assert campaign.dialogues
    assert campaign.quests
    assert campaign.shops
    assert any(
        interaction.interaction_id == "interaction:stonefall-trigger"
        for interaction in campaign.interactions
    )
    assert any(
        item.item_id == "item:rope-coil" and "slot:utility" in item.slots
        for item in campaign.equipment_compatibility
    )


def test_bridge_supplies_and_enforces_equipment_choices() -> None:
    bridge = _bridge()
    _command(
        bridge,
        "world.start",
        {"party_ids": ["actor:hero-a"]},
        "start",
    )
    _command(
        bridge,
        "world.travel",
        {"area_id": "area:market-row"},
        "market",
    )
    _command(
        bridge,
        "shop.buy",
        {
            "shop_id": "shop:reedhollow-supplies",
            "item_id": "item:rope-coil",
            "quantity": 1,
        },
        "buy-rope",
    )

    options = bridge.handle_message(
        _request(
            "query.request",
            {"query_type": "inventory.equipment_options", "query": {}},
            "equipment-options",
        )
    )
    rows = _payload(options)
    assert rows["party_ids"] == ["actor:hero-a"]
    rope = next(item for item in rows["items"] if item["item_id"] == "item:rope-coil")
    assert rope["slots"] == [{"slot_id": "slot:utility", "label": "Utility"}]

    accepted = _command(
        bridge,
        "inventory.equip",
        {
            "actor_id": "actor:hero-a",
            "item_id": "item:rope-coil",
            "slot": "slot:utility",
        },
        "equip-rope",
    )
    assert accepted is not None
    assert accepted["kind"] == "command.accepted"

    rejected = _command(
        bridge,
        "inventory.equip",
        {
            "actor_id": "actor:hero-a",
            "item_id": "item:rope-coil",
            "slot": "slot:main-hand",
        },
        "equip-rope-invalid",
    )
    assert rejected is not None
    assert rejected["kind"] == "command.rejected"
    assert rejected["ok"] is False


def test_world_actions_expose_authoritative_exploration_and_trade_state() -> None:
    bridge = _bridge()
    _command(
        bridge,
        "world.start",
        {"party_ids": ["actor:hero-a"]},
        "start-actions",
    )
    _command(
        bridge,
        "world.travel",
        {"area_id": "area:market-row"},
        "market-actions",
    )

    before = bridge.handle_message(
        _request(
            "query.request",
            {"query_type": "world.actions", "query": {}},
            "actions-before-buy",
        )
    )
    rows = _payload(before)
    assert rows["area_name"] == "Market Row"
    assert "shop" in rows["area_tags"]
    assert rows["exploration_prompt"]
    rope = next(
        item
        for shop in rows["shops"]
        for item in shop["items"]
        if item["item_id"] == "item:rope-coil"
    )
    assert rope["owned_quantity"] == 0
    assert rope["buy_available"] is True
    assert rope["sell_available"] is False

    _command(
        bridge,
        "shop.buy",
        {
            "shop_id": "shop:reedhollow-supplies",
            "item_id": "item:rope-coil",
            "quantity": 1,
        },
        "buy-actions-rope",
    )
    after = bridge.handle_message(
        _request(
            "query.request",
            {"query_type": "world.actions", "query": {}},
            "actions-after-buy",
        )
    )
    rows_after = _payload(after)
    rope_after = next(
        item
        for shop in rows_after["shops"]
        for item in shop["items"]
        if item["item_id"] == "item:rope-coil"
    )
    assert rope_after["owned_quantity"] == 1
    assert rope_after["sell_available"] is True


def test_begin_encounter_resyncs_tactical_stream_and_blocks_world_progress() -> None:
    bridge = _bridge()
    bridge.spell_tactical = SpellEnabledTacticalSession.create(
        campaign_id="campaign:v1-completion",
        session_id="session:v1-completion",
        seed=19,
    )
    bridge.spell_tactical.tactical.sequence = 6
    _advance_to_road_encounter(bridge)

    started = _command(
        bridge,
        "world.begin_encounter",
        {"encounter_id": "encounter:road-ambush"},
        "begin-road-ambush",
    )
    assert started is not None
    assert started["kind"] == "command.accepted"
    started_payload = _payload(started)
    tactical_snapshot = started_payload["snapshot"]
    assert isinstance(tactical_snapshot, dict)
    tactical_state = tactical_snapshot["state"]
    assert isinstance(tactical_state, dict)
    assert tactical_state["sequence"] == 7
    assert started_payload["result"]["tactical_sequence"] == 7
    assert bridge.active_world_encounter_id == "encounter:road-ambush"

    actions = bridge.handle_message(
        _request(
            "query.request",
            {"query_type": "world.actions", "query": {}},
            "road-actions-during-combat",
        )
    )
    rows = _payload(actions)
    assert "active tactical encounter" in rows["exploration_prompt"]
    assert rows["can_rest"] is False
    assert rows["dialogues"] == []
    assert all(row["available"] is False for row in rows["travel"])
    assert all(
        "active tactical encounter" in row["reason"]
        for row in rows["travel"]
    )

    blocked = _command(
        bridge,
        "world.travel",
        {"area_id": "area:reedhollow-square"},
        "blocked-travel-during-combat",
    )
    assert blocked is not None
    assert blocked["kind"] == "command.rejected"
    assert blocked["ok"] is False
    assert bridge.world.state.current_area_id == "area:old-road"


def test_end_to_end_campaign_completes_after_save_restore() -> None:
    runtime = WorldRuntime(demo_campaign(), seed=97)
    _runtime_command(runtime, "world.start", {"party_ids": ["actor:hero-a"]})
    _runtime_command(
        runtime,
        "dialogue.start",
        {"dialogue_id": "dialogue:warden-ilar"},
    )
    _runtime_command(
        runtime,
        "dialogue.choose",
        {"choice_id": "choice:accept-quarry"},
    )
    _runtime_command(
        runtime,
        "dialogue.choose",
        {"choice_id": "choice:leave-warden"},
    )

    _runtime_command(runtime, "world.travel", {"area_id": "area:market-row"})
    _runtime_command(
        runtime,
        "shop.buy",
        {
            "shop_id": "shop:reedhollow-supplies",
            "item_id": "item:rope-coil",
            "quantity": 1,
        },
    )
    _runtime_command(runtime, "world.rest", {})
    _runtime_command(
        runtime,
        "shop.sell",
        {
            "shop_id": "shop:reedhollow-supplies",
            "item_id": "item:rope-coil",
            "quantity": 1,
        },
    )
    _runtime_command(runtime, "world.travel", {"area_id": "area:reedhollow-square"})
    _runtime_command(runtime, "world.travel", {"area_id": "area:old-road"})
    _runtime_command(
        runtime,
        "world.resolve_interaction",
        {"interaction_id": "interaction:collapsed-marker", "bonus": 30},
    )
    _runtime_command(
        runtime,
        "world.complete_encounter",
        {"encounter_id": "encounter:road-ambush"},
    )
    _runtime_command(runtime, "world.travel", {"area_id": "area:quarry-mouth"})
    _runtime_command(
        runtime,
        "world.resolve_interaction",
        {"interaction_id": "interaction:flooded-gate", "bonus": 30},
    )
    _runtime_command(
        runtime,
        "world.complete_encounter",
        {"encounter_id": "encounter:quarry-watchers"},
    )
    _runtime_command(runtime, "world.travel", {"area_id": "area:underworks"})
    _runtime_command(
        runtime,
        "world.resolve_interaction",
        {"interaction_id": "interaction:stonefall-trigger", "bonus": 30},
    )
    _runtime_command(
        runtime,
        "world.resolve_interaction",
        {"interaction_id": "interaction:survey-lantern", "bonus": 30},
    )
    _runtime_command(
        runtime,
        "dialogue.start",
        {"dialogue_id": "dialogue:surveyor-echo"},
    )
    _runtime_command(
        runtime,
        "dialogue.choose",
        {"choice_id": "choice:keep-lantern"},
    )

    saved = runtime.snapshot()
    restored = restore_world_runtime(demo_campaign(), saved)
    assert restored.state == runtime.state
    assert restored.rng.snapshot() == runtime.rng.snapshot()

    _runtime_command(
        restored,
        "world.complete_encounter",
        {"encounter_id": "encounter:underworks-swarm"},
    )
    _runtime_command(restored, "world.travel", {"area_id": "area:lantern-vault"})
    _runtime_command(
        restored,
        "world.complete_encounter",
        {"encounter_id": "encounter:vault-warden"},
    )

    assert "flag:campaign-complete" in restored.state.flags
    assert "flag:lantern-kept" in restored.state.flags
    assert "flag:stonefall-disarmed" in restored.state.flags
    assert len(restored.state.completed_encounters) == 4
    assert restored.state.rest_count == 1
