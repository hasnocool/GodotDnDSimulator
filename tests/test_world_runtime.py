# tests/test_world_runtime.py
from __future__ import annotations

from godot_dnd_engine.world import QuestStatus, WorldRuntime, demo_campaign, replay_world_events


def _runtime(seed: int = 31) -> WorldRuntime:
    return WorldRuntime(demo_campaign(), seed=seed)


def _command(runtime: WorldRuntime, command_type: str, payload: dict[str, object]) -> dict[str, object]:
    return runtime.handle_command(
        command_type,
        payload,
        expected_sequence=runtime.state.sequence,
    )


def test_world_start_travel_and_actions_are_authoritative() -> None:
    runtime = _runtime()
    _command(runtime, "world.start", {"party_ids": ["actor:hero-a", "actor:hero-b"]})
    actions = runtime.query("world.actions", {})
    destinations = {item["area_id"] for item in actions["travel"]}
    assert destinations == {"area:old-road", "area:market-row"}

    _command(runtime, "world.travel", {"area_id": "area:old-road"})
    assert runtime.state.current_area_id == "area:old-road"
    assert "visited:area:old-road" in runtime.state.flags


def test_dialogue_choice_activates_branching_quest_state() -> None:
    runtime = _runtime()
    _command(runtime, "world.start", {"party_ids": ["actor:hero-a"]})
    _command(runtime, "dialogue.start", {"dialogue_id": "dialogue:warden-ilar"})
    dialogue = runtime.query("dialogue.current", {})
    assert dialogue["speaker"] == "Warden Ilar"
    assert {row["choice_id"] for row in dialogue["choices"]} == {
        "choice:accept-quarry",
        "choice:decline-quarry",
    }

    _command(runtime, "dialogue.choose", {"choice_id": "choice:accept-quarry"})
    assert runtime.state.quest_map()["quest:lanterns-below"] is QuestStatus.ACTIVE
    assert "flag:quarry-mission" in runtime.state.flags


def test_skill_interaction_is_deterministic_and_records_rng_checkpoint() -> None:
    first = _runtime(seed=97)
    second = _runtime(seed=97)
    for runtime in (first, second):
        _command(runtime, "world.start", {"party_ids": ["actor:hero-a"]})
        _command(runtime, "world.travel", {"area_id": "area:old-road"})
        _command(
            runtime,
            "world.resolve_interaction",
            {"interaction_id": "interaction:collapsed-marker", "bonus": 3},
        )

    first_event = first.events[-1]
    second_event = second.events[-1]
    assert first_event == second_event
    assert first_event.rng_after is not None
    payload = first_event.payload_map()
    assert 1 <= int(payload["roll"]) <= 20
    assert int(payload["total"]) == int(payload["roll"]) + 3


def test_shop_inventory_equipment_and_currency_flow() -> None:
    runtime = _runtime()
    _command(runtime, "world.start", {"party_ids": ["actor:hero-a"]})
    _command(runtime, "world.travel", {"area_id": "area:market-row"})
    before = runtime.state.currency
    _command(
        runtime,
        "shop.buy",
        {"shop_id": "shop:reedhollow-supplies", "item_id": "item:rope-coil", "quantity": 1},
    )
    assert runtime.state.inventory_map()["item:rope-coil"] == 1
    assert runtime.state.currency == before - 5
    _command(
        runtime,
        "inventory.equip",
        {"actor_id": "actor:hero-a", "slot": "slot:utility", "item_id": "item:rope-coil"},
    )
    assert runtime.state.equipped_map()["actor:hero-a|slot:utility"] == "item:rope-coil"
    _command(
        runtime,
        "shop.sell",
        {"shop_id": "shop:reedhollow-supplies", "item_id": "item:rope-coil", "quantity": 1},
    )
    assert "item:rope-coil" not in runtime.state.inventory_map()


def test_encounter_completion_gates_full_village_to_boss_route() -> None:
    runtime = _runtime()
    _command(runtime, "world.start", {"party_ids": ["actor:hero-a"]})
    _command(runtime, "dialogue.start", {"dialogue_id": "dialogue:warden-ilar"})
    _command(runtime, "dialogue.choose", {"choice_id": "choice:accept-quarry"})
    _command(runtime, "dialogue.choose", {"choice_id": "choice:leave-warden"})
    _command(runtime, "world.travel", {"area_id": "area:old-road"})
    _command(runtime, "world.complete_encounter", {"encounter_id": "encounter:road-ambush"})
    _command(runtime, "world.travel", {"area_id": "area:quarry-mouth"})
    _command(runtime, "world.complete_encounter", {"encounter_id": "encounter:quarry-watchers"})
    _command(runtime, "world.travel", {"area_id": "area:underworks"})
    _command(runtime, "world.complete_encounter", {"encounter_id": "encounter:underworks-swarm"})
    _command(runtime, "world.travel", {"area_id": "area:lantern-vault"})
    _command(runtime, "world.complete_encounter", {"encounter_id": "encounter:vault-warden"})

    assert "flag:campaign-complete" in runtime.state.flags
    assert "encounter:vault-warden" in runtime.state.completed_encounters


def test_world_events_replay_to_same_visible_state() -> None:
    runtime = _runtime()
    initial = runtime.state
    _command(runtime, "world.start", {"party_ids": ["actor:hero-a"]})
    _command(runtime, "world.travel", {"area_id": "area:market-row"})
    _command(runtime, "world.rest", {})

    replayed = replay_world_events(initial, tuple(runtime.events))
    assert replayed == runtime.state
    snapshot = runtime.snapshot()
    assert snapshot["rng"]["algorithm"] == "pcg32-v1"
    assert len(snapshot["events"]) == 3
