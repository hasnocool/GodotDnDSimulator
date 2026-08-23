extends SceneTree

const Protocol = preload("res://bridge/bridge_protocol.gd")
const FakeTransportScript = preload("res://bridge/fake_engine_transport.gd")

var _failures := 0


func _initialize() -> void:
    call_deferred("_run")


func _run() -> void:
    await _test_world_overlay_uses_isolated_authoritative_stream()
    if _failures == 0:
        print("Godot world RPG tests: PASS")
        quit(0)
    else:
        push_error("Godot world RPG tests: %d failure(s)" % _failures)
        quit(1)


func _test_world_overlay_uses_isolated_authoritative_stream() -> void:
    var shell_scene := load("res://scenes/shell/app_shell.tscn") as PackedScene
    _check(shell_scene != null, "app shell loads for world RPG test")
    if shell_scene == null:
        return
    var shell = shell_scene.instantiate()
    var transport = FakeTransportScript.new()
    shell.transport_override = transport
    root.add_child(shell)
    await process_frame

    var hello := _last_message(transport, "bridge.hello")
    _check(not hello.is_empty(), "world shell sends bridge hello")
    transport.queue_message(
        Protocol.make_response(
            "bridge.hello.accepted",
            str(hello["request_id"]),
            str(hello["correlation_id"]),
            int(hello["generation"]),
            true,
            {
                "protocol": Protocol.PROTOCOL_NAME,
                "capabilities": [
                    "commands.v1",
                    "queries.v1",
                    "previews.v1",
                    "snapshots.v1",
                    "events.v1",
                    "request-cancel.v1",
                    "request-generation.v1",
                    "world.runtime.v1",
                    "world.commands.v1",
                    "world.queries.v1",
                    "world.save-replay.v1",
                    "dialogue.v1",
                    "quests.v1",
                    "shops.v1",
                ],
            },
        )
    )
    await process_frame

    var snapshot_request := _last_query(transport, "bridge.snapshot")
    _check(not snapshot_request.is_empty(), "core shell requests initial snapshot")
    transport.queue_message(
        Protocol.make_response(
            "query.result",
            str(snapshot_request["request_id"]),
            str(snapshot_request["correlation_id"]),
            int(snapshot_request["generation"]),
            true,
            {"snapshot": _core_snapshot()},
        )
    )
    for _index in range(60):
        await process_frame
        if shell.shell_state() == shell.ShellState.READY:
            break
    _check(shell.shell_state() == shell.ShellState.READY, "shell becomes ready")

    var launcher: Button = shell.get_node("ShellUI/WorldButton")
    _check(launcher.visible, "Adventure launcher is capability gated")
    launcher.pressed.emit()
    await process_frame
    var world = shell.get_node("WorldRPG")
    _check(world.visible, "Adventure launcher opens world overlay")

    var world_snapshot_request := _last_query(transport, "world.snapshot")
    var actions_request := _last_query(transport, "world.actions")
    var journal_request := _last_query(transport, "world.journal")
    var map_request := _last_query(transport, "world.map")
    var party_request := _last_query(transport, "world.party")
    _check(not world_snapshot_request.is_empty(), "world overlay requests world snapshot")
    _check(not actions_request.is_empty(), "world overlay requests available actions")
    _check(not journal_request.is_empty(), "world overlay requests journal")
    _check(not map_request.is_empty(), "world overlay requests authoritative map")
    _check(not party_request.is_empty(), "world overlay requests authoritative party")

    transport.queue_message(
        Protocol.make_response(
            "query.result",
            str(world_snapshot_request["request_id"]),
            str(world_snapshot_request["correlation_id"]),
            int(world_snapshot_request["generation"]),
            true,
            {"world_snapshot": _world_snapshot(0)},
        )
    )
    transport.queue_message(
        Protocol.make_response(
            "query.result",
            str(actions_request["request_id"]),
            str(actions_request["correlation_id"]),
            int(actions_request["generation"]),
            true,
            {
                "area_id": "area:reedhollow-square",
                "travel": [{"area_id": "area:old-road", "name": "Old Quarry Road"}],
                "dialogues": [{"dialogue_id": "dialogue:warden-ilar", "name": "Warden Ilar"}],
                "interactions": [],
                "encounters": [],
                "shops": [],
                "can_rest": true,
            },
        )
    )
    transport.queue_message(
        Protocol.make_response(
            "query.result",
            str(journal_request["request_id"]),
            str(journal_request["correlation_id"]),
            int(journal_request["generation"]),
            true,
            {"quests": {"quest:test": "available"}, "entries": ["Arrival"]},
        )
    )
    transport.queue_message(
        Protocol.make_response(
            "query.result",
            str(map_request["request_id"]),
            str(map_request["correlation_id"]),
            int(map_request["generation"]),
            true,
            {
                "current_area_id": "area:reedhollow-square",
                "areas": [
                    {
                        "area_id": "area:reedhollow-square",
                        "name": "Reedhollow Square",
                        "exits": ["area:old-road"],
                        "visited": true,
                    },
                    {
                        "area_id": "area:old-road",
                        "name": "Old Quarry Road",
                        "exits": ["area:reedhollow-square"],
                        "visited": false,
                    },
                ],
            },
        )
    )
    transport.queue_message(
        Protocol.make_response(
            "query.result",
            str(party_request["request_id"]),
            str(party_request["correlation_id"]),
            int(party_request["generation"]),
            true,
            {
                "party_ids": ["actor:ember-warden", "actor:lantern-scout"],
                "equipped": {"actor:ember-warden:main_hand": "item:lantern-blade"},
            },
        )
    )
    await process_frame

    _check(
        world.call("world_snapshot")["state"]["mode"] == "world",
        "world snapshot is stored by the world view",
    )
    _check(
        shell.client_state().authoritative.state_view().get("mode", "") != "world",
        "world query does not replace tactical/core authoritative mirror",
    )
    var travel_box = world.get_node("Panel/Margin/VBox/Columns/ActionsScroll/Actions/Travel")
    _check(travel_box.get_child_count() == 1, "travel UI renders engine-returned actions")

    var map_view: RichTextLabel = world.get_node("Panel/Margin/VBox/Columns/ManagementTabs/Map")
    var party_view: RichTextLabel = world.get_node("Panel/Margin/VBox/Columns/ManagementTabs/Party")
    var inventory_view: RichTextLabel = world.get_node("Panel/Margin/VBox/Columns/ManagementTabs/Inventory")
    var journal_view: RichTextLabel = world.get_node("Panel/Margin/VBox/Columns/ManagementTabs/Journal")
    _check(map_view.text.contains("Reedhollow Square"), "map tab renders authoritative area data")
    _check(map_view.text.contains("Old Quarry Road"), "map tab renders connected area data")
    _check(party_view.text.contains("actor:ember-warden"), "party tab renders authoritative party IDs")
    _check(party_view.text.contains("item:lantern-blade"), "party tab renders authoritative equipment")
    _check(inventory_view.text.contains("item:field-kit"), "inventory tab renders snapshot inventory")
    _check(inventory_view.text.contains("Currency: 25"), "inventory tab renders authoritative currency")
    _check(journal_view.text.contains("quest:test"), "journal tab renders authoritative quest state")

    shell.shutdown()
    root.remove_child(shell)
    shell.queue_free()
    await process_frame


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


func _world_snapshot(sequence: int) -> Dictionary:
    return {
        "schema_version": 1,
        "state": {
            "campaign_id": "campaign:test",
            "sequence": sequence,
            "mode": "world",
            "area": {"area_id": "area:reedhollow-square", "name": "Reedhollow Square", "tags": ["village"]},
            "party_ids": ["actor:ember-warden", "actor:lantern-scout"],
            "flags": [],
            "quests": {"quest:test": "available"},
            "inventory": {"item:field-kit": 2},
            "equipped": {"actor:ember-warden:main_hand": "item:lantern-blade"},
            "currency": 25,
            "active_dialogue": null,
            "completed_encounters": [],
            "journal": ["Arrival"],
            "rest_count": 0,
        },
        "rng": {"algorithm": "pcg32-v1", "state": 1, "increment": 3},
        "events": [],
    }


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


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error(message)
