extends SceneTree

const Protocol = preload("res://bridge/bridge_protocol.gd")
const EngineBridgeScript = preload("res://bridge/engine_bridge.gd")
const FakeTransportScript = preload("res://bridge/fake_engine_transport.gd")
const CoordinatorScript = preload("res://state/client_state_coordinator.gd")
const SaveStoreScript = preload("res://scenes/world/world_save_store.gd")

var _failures := 0


func _initialize() -> void:
    call_deferred("_run")


func _run() -> void:
    await _test_world_save_load_roundtrip()
    await _test_disconnect_clears_pending_save_ui()
    await _test_adventure_scene_reconciles_only_authoritative_loads()
    if _failures == 0:
        print("Godot world save/load tests: PASS")
        quit(0)
    else:
        push_error("Godot world save/load tests: %d failure(s)" % _failures)
        quit(1)


func _test_world_save_load_roundtrip() -> void:
    var root_dir := "user://tests/world-save-load-%d" % Time.get_ticks_usec()
    var store = SaveStoreScript.new(root_dir)
    var invalid_failures: Array = []
    store.operation_failed.connect(
        func(operation: String, slot_id: String, user_message: String, debug_detail: String) -> void:
            invalid_failures.append([operation, slot_id, user_message, debug_detail])
    )
    _check(not store.load_slot("../escape"), "save store rejects non-whitelisted slot paths")
    _check(invalid_failures.size() == 1, "invalid slot rejection is surfaced")

    var panel_scene := load("res://scenes/world/world_save_panel.tscn") as PackedScene
    _check(panel_scene != null, "save/load panel scene loads")
    if panel_scene == null:
        return
    var panel = panel_scene.instantiate()
    root.add_child(panel)
    await process_frame
    panel.call("bind_save_store", store)

    var bridge = EngineBridgeScript.new()
    var transport = FakeTransportScript.new()
    var coordinator = CoordinatorScript.new()
    coordinator.bind_bridge(bridge)
    _check(bridge.initialize(transport) == OK, "save/load test bridge initializes")
    var hello := _last_message(transport, "bridge.hello")
    _check(not hello.is_empty(), "save/load test sends bridge hello")
    transport.queue_message(
        Protocol.make_response(
            "bridge.hello.accepted",
            str(hello["request_id"]),
            str(hello["correlation_id"]),
            int(hello["generation"]),
            true,
            {
                "protocol": Protocol.PROTOCOL_NAME,
                "capabilities": ["commands.v1", "queries.v1", "world.save-replay.v1"],
            },
        )
    )
    bridge.poll(0.0)
    coordinator.authoritative.ingest_snapshot(_core_snapshot())
    panel.call("bind_client_state", coordinator)

    var active_snapshot := _world_snapshot(9, "Reedhollow Square")
    panel.call("set_world_snapshot", active_snapshot)
    panel.call("activate")
    _check(await _wait_for_store(store), "initial save-slot listing completes off the frame loop")
    await process_frame

    var save_button: Button = panel.get_node("Buttons/SaveGame")
    _check(not save_button.disabled, "save is enabled when authoritative world state exists")
    save_button.pressed.emit()
    await process_frame
    var save_request := _last_query(transport, "world.save")
    _check(not save_request.is_empty(), "Save Game requests an authoritative world.save snapshot")
    var save_request_payload: Dictionary = save_request.get("payload", {})
    var save_query: Dictionary = save_request_payload.get("query", {})
    _check(
        str(save_query.get("encoding", "")) == "lossless-json",
        "Save Game explicitly requests the lossless engine encoding",
    )

    var saved_snapshot := _world_snapshot(5, "Old Quarry Road")
    var saved_snapshot_json := _lossless_world_snapshot_json(5, "Old Quarry Road")
    transport.queue_message(
        Protocol.make_response(
            "query.result",
            str(save_request["request_id"]),
            str(save_request["correlation_id"]),
            int(save_request["generation"]),
            true,
            {
                "world_snapshot_json": saved_snapshot_json,
                "save_metadata": {
                    "campaign_id": "campaign:test",
                    "sequence": 5,
                    "area_id": "area:test-5",
                    "area_name": "Old Quarry Road",
                },
            },
        )
    )
    bridge.poll(0.0)
    _check(await _wait_for_store(store), "threaded save write completes")
    await process_frame

    var save_path := ProjectSettings.globalize_path(root_dir).path_join("slot-1.json")
    _check(FileAccess.file_exists(save_path), "save slot is persisted under the configured user path")
    var save_file := FileAccess.open(save_path, FileAccess.READ)
    _check(save_file != null, "persisted save file can be inspected")
    if save_file != null:
        var persisted_text := save_file.get_as_text()
        save_file.close()
        _check(
            persisted_text.contains("9223372036854775001"),
            "persisted save preserves 64-bit RNG digits as engine-owned text",
        )

    var load_button: Button = panel.get_node("Buttons/LoadGame")
    _check(not load_button.disabled, "saved slot becomes loadable")
    var details: Label = panel.get_node("SaveDetails")
    _check(details.text.contains("Old Quarry Road"), "slot metadata shows the saved area")
    _check(details.text.contains("world sequence 5"), "slot metadata shows the saved sequence")

    panel.call("set_world_snapshot", active_snapshot)
    load_button.pressed.emit()
    _check(await _wait_for_store(store), "threaded save read completes")
    await process_frame
    var load_request := _last_message(transport, "command.submit")
    _check(not load_request.is_empty(), "Load Game submits an authoritative command")
    var command_payload: Dictionary = load_request.get("payload", {})
    var command: Dictionary = command_payload.get("command", {})
    _check(str(command.get("command_type", "")) == "world.load", "load uses world.load")
    _check(int(command.get("expected_sequence", -1)) == 9, "load validates against the current world sequence")
    var load_payload: Dictionary = command.get("payload", {})
    _check(
        str(load_payload.get("world_snapshot_json", "")) == saved_snapshot_json,
        "load submits the lossless engine snapshot string unchanged",
    )
    var panel_snapshot: Dictionary = panel.get("_world_snapshot")
    _check(
        int((panel_snapshot.get("state", {}) as Dictionary).get("sequence", -1)) == 9,
        "reading a save never optimistically replaces displayed world state",
    )

    transport.queue_message(
        Protocol.make_response(
            "command.accepted",
            str(load_request["request_id"]),
            str(load_request["correlation_id"]),
            int(load_request["generation"]),
            true,
            {"world_snapshot": saved_snapshot, "world_events": [], "presentation_events": []},
        )
    )
    bridge.poll(0.0)
    var status: Label = panel.get_node("SaveStatus")
    _check(status.text.contains("loaded and validated"), "accepted load reports engine validation")

    bridge.shutdown()
    root.remove_child(panel)
    panel.queue_free()
    await process_frame
    _cleanup_test_root(root_dir)


func _test_disconnect_clears_pending_save_ui() -> void:
    var panel_scene := load("res://scenes/world/world_save_panel.tscn") as PackedScene
    if panel_scene == null:
        _check(false, "save/load panel loads for disconnect regression")
        return
    var panel = panel_scene.instantiate()
    root.add_child(panel)
    await process_frame

    var bridge = EngineBridgeScript.new()
    var transport = FakeTransportScript.new()
    var coordinator = CoordinatorScript.new()
    coordinator.bind_bridge(bridge)
    _check(bridge.initialize(transport) == OK, "disconnect test bridge initializes")
    var hello := _last_message(transport, "bridge.hello")
    transport.queue_message(
        Protocol.make_response(
            "bridge.hello.accepted",
            str(hello["request_id"]),
            str(hello["correlation_id"]),
            int(hello["generation"]),
            true,
            {
                "protocol": Protocol.PROTOCOL_NAME,
                "capabilities": ["commands.v1", "queries.v1", "world.save-replay.v1"],
            },
        )
    )
    bridge.poll(0.0)
    coordinator.authoritative.ingest_snapshot(_core_snapshot())
    panel.call("bind_client_state", coordinator)
    panel.call("set_world_snapshot", _world_snapshot(3, "Reedhollow Square"))

    var save_button: Button = panel.get_node("Buttons/SaveGame")
    save_button.pressed.emit()
    await process_frame
    _check(
        not str(panel.get("_save_query_slot")).is_empty(),
        "disconnect regression starts with a pending save query",
    )
    transport.simulate_disconnect("cable removed")
    await process_frame
    _check(
        str(panel.get("_save_query_slot")).is_empty(),
        "bridge disconnect clears the pending save query slot",
    )
    _check(
        not bool(panel.call("_operation_in_progress")),
        "bridge disconnect does not leave save/load controls permanently busy",
    )
    var status: Label = panel.get_node("SaveStatus")
    _check(status.text.contains("connection lost"), "disconnect is visible to the save/load user")

    bridge.shutdown()
    root.remove_child(panel)
    panel.queue_free()
    await process_frame


func _test_adventure_scene_reconciles_only_authoritative_loads() -> void:
    var world_scene := load("res://scenes/world/world_rpg_view.tscn") as PackedScene
    _check(world_scene != null, "Adventure scene with Save/Load tab loads")
    if world_scene == null:
        return
    var world = world_scene.instantiate()
    root.add_child(world)
    await process_frame
    var save_panel = world.get_node("Panel/Margin/VBox/Columns/ManagementTabs/SaveLoad")
    _check(save_panel != null, "Adventure management tabs include SaveLoad")

    var active_snapshot := _world_snapshot(9, "Reedhollow Square")
    var loaded_snapshot := _world_snapshot(5, "Old Quarry Road")
    world.call("_apply_snapshot", active_snapshot)
    _check(
        int((save_panel.get("_world_snapshot") as Dictionary)["state"]["sequence"]) == 9,
        "Adventure forwards accepted world snapshots to save/load presentation",
    )
    world.call(
        "_on_command_payload",
        "world:load-file:slot-1",
        {"world_snapshot": loaded_snapshot},
    )
    _check(
        int(world.call("world_snapshot")["state"]["sequence"]) == 5,
        "authoritative world.load payload reconciles the Adventure world snapshot",
    )
    _check(
        int((save_panel.get("_world_snapshot") as Dictionary)["state"]["sequence"]) == 5,
        "accepted load reconciliation reaches the Save/Load panel",
    )

    root.remove_child(world)
    world.queue_free()
    await process_frame


func _wait_for_store(store, frames: int = 240) -> bool:
    for _index in range(frames):
        await process_frame
        if not store.is_busy():
            return true
    return false


func _last_message(transport, kind: String) -> Dictionary:
    for index in range(transport.sent_messages.size() - 1, -1, -1):
        var message: Dictionary = transport.sent_messages[index]
        if str(message.get("kind", "")) == kind:
            return message
    return {}


func _last_query(transport, query_type: String) -> Dictionary:
    for index in range(transport.sent_messages.size() - 1, -1, -1):
        var message: Dictionary = transport.sent_messages[index]
        if str(message.get("kind", "")) != "query.request":
            continue
        var payload: Dictionary = message.get("payload", {})
        if str(payload.get("query_type", "")) == query_type:
            return message
    return {}


func _core_snapshot() -> Dictionary:
    return {
        "schema_version": 1,
        "state": {
            "campaign_id": "campaign:test",
            "session_id": "session:test",
            "sequence": 0,
            "tick": 0,
        },
        "rng": {"algorithm": "pcg32-v1", "state": 1, "increment": 3},
    }


func _world_snapshot(sequence: int, area_name: String) -> Dictionary:
    return {
        "schema_version": 1,
        "state": {
            "campaign_id": "campaign:test",
            "sequence": sequence,
            "mode": "world",
            "area": {
                "area_id": "area:test-%d" % sequence,
                "name": area_name,
                "tags": [],
            },
            "party_ids": [],
            "flags": [],
            "quests": {},
            "inventory": {},
            "equipped": {},
            "currency": 0,
            "active_dialogue": null,
            "completed_encounters": [],
            "journal": [],
            "rest_count": 0,
        },
        "rng": {"algorithm": "pcg32-v1", "state": sequence + 1, "increment": 3},
        "events": [],
    }


func _lossless_world_snapshot_json(sequence: int, area_name: String) -> String:
    return (
        "{\"events\":[],\"rng\":{\"algorithm\":\"pcg32-v1\","
        + "\"increment\":1442695040888963407,\"state\":9223372036854775001},"
        + "\"schema_version\":1,\"state\":{\"active_dialogue\":null,"
        + "\"area\":{\"area_id\":\"area:test-%d\",\"name\":\"%s\",\"tags\":[]},"
        % [sequence, area_name]
        + "\"campaign_id\":\"campaign:test\",\"completed_encounters\":[],"
        + "\"currency\":0,\"equipped\":{},\"flags\":[],\"inventory\":{},"
        + "\"journal\":[],\"mode\":\"world\",\"party_ids\":[],\"quests\":{},"
        + "\"rest_count\":0,\"sequence\":%d}}" % sequence
    )


func _cleanup_test_root(root_dir: String) -> void:
    var root_path := ProjectSettings.globalize_path(root_dir)
    for slot_id in ["slot-1", "slot-2", "slot-3"]:
        for suffix in [".json", ".json.tmp", ".json.bak"]:
            var path := root_path.path_join("%s%s" % [slot_id, suffix])
            if FileAccess.file_exists(path):
                DirAccess.remove_absolute(path)
    DirAccess.remove_absolute(root_path)


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error(message)
