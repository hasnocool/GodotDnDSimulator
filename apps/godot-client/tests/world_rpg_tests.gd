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
                    "characters.creator.v1",
                    "characters.creator.commands.v1",
                    "characters.levelup.v1",
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
                "party_ids": ["actor:premade-mira", "actor:premade-aster"],
                "equipped": {"actor:premade-mira|main_hand": "item:lantern-blade"},
            },
        )
    )
    await process_frame

    var mira_request := _last_character_query(transport, "actor:premade-mira")
    var aster_request := _last_character_query(transport, "actor:premade-aster")
    _check(not mira_request.is_empty(), "party card requests Mira character record")
    _check(not aster_request.is_empty(), "party card requests Aster character record")
    transport.queue_message(
        _character_response(
            mira_request,
            _character_record(
                "actor:premade-mira",
                "Mira Quill",
                "guardian",
                18,
                16,
            ),
        )
    )
    transport.queue_message(
        _character_response(
            aster_request,
            _character_record(
                "actor:premade-aster",
                "Aster Vale",
                "scholar",
                12,
                13,
            ),
        )
    )
    await process_frame
    _check(
        _count_character_queries(transport, "actor:premade-mira") == 1,
        "partial party-card responses do not duplicate Mira queries",
    )
    _check(
        _count_character_queries(transport, "actor:premade-aster") == 1,
        "partial party-card responses do not duplicate Aster queries",
    )

    _check(
        world.call("world_snapshot")["state"]["mode"] == "world",
        "world snapshot is stored by the world view",
    )
    _check(
        shell.client_state().authoritative.state_view().get("mode", "") != "world",
        "world query does not replace tactical/core authoritative mirror",
    )
    var travel_box = world.get_node(
        "Panel/Margin/VBox/Columns/ActionsScroll/Actions/Travel"
    )
    _check(travel_box.get_child_count() == 1, "travel UI renders engine-returned actions")

    var map_view: RichTextLabel = world.get_node(
        "Panel/Margin/VBox/Columns/ManagementTabs/Map"
    )
    var party_cards: VBoxContainer = world.get_node(
        "Panel/Margin/VBox/Columns/ManagementTabs/Party/PartyCards"
    )
    var inventory_items: VBoxContainer = world.get_node(
        "Panel/Margin/VBox/Columns/ManagementTabs/Inventory/ItemsScroll/InventoryItems"
    )
    var journal_view: RichTextLabel = world.get_node(
        "Panel/Margin/VBox/Columns/ManagementTabs/Journal"
    )
    _check(map_view.text.contains("Reedhollow Square"), "map tab renders authoritative area data")
    _check(map_view.text.contains("Old Quarry Road"), "map tab renders connected area data")
    _check(
        _tree_text(party_cards).contains("Mira Quill"),
        "party cards render authoritative character names",
    )
    _check(
        _tree_text(party_cards).contains("HP 18/18 · AC 16"),
        "party cards render authoritative actor stats",
    )
    _check(
        _tree_text(party_cards).contains("main_hand = item:lantern-blade"),
        "party cards parse authoritative actor|slot equipment keys",
    )
    _check(
        _tree_text(inventory_items).contains("item:field-kit × 2"),
        "inventory tab renders snapshot inventory",
    )
    _check(journal_view.text.contains("quest:test"), "journal tab renders authoritative quest state")

    var equip_slot: LineEdit = world.get_node(
        "Panel/Margin/VBox/Columns/ManagementTabs/Inventory/EquipRow/EquipSlot"
    )
    var equip_button: Button = world.get_node(
        "Panel/Margin/VBox/Columns/ManagementTabs/Inventory/EquipRow/Equip"
    )
    equip_slot.text = "main_hand"
    equip_button.pressed.emit()
    await process_frame
    var equip_command := _last_message(transport, "command.submit")
    _check(not equip_command.is_empty(), "inventory UI submits an authoritative command")
    var command_payload: Dictionary = equip_command.get("payload", {})
    var equip_payload: Dictionary = command_payload.get("command", {})
    _check(
        str(equip_payload.get("command_type", "")) == "inventory.equip",
        "inventory UI uses inventory.equip",
    )
    _check(
        int(equip_payload.get("expected_sequence", -1)) == 0,
        "equipment command uses isolated world sequence",
    )
    var equipment_intent: Dictionary = equip_payload.get("payload", {})
    _check(
        str(equipment_intent.get("actor_id", "")) == "actor:premade-mira",
        "equipment intent targets selected party actor",
    )
    _check(
        str(equipment_intent.get("item_id", "")) == "item:field-kit",
        "equipment intent uses an owned item",
    )
    _check(
        str(equipment_intent.get("slot", "")) == "main_hand",
        "equipment slot is submitted as intent for engine validation",
    )

    world.hide_world()
    world.show_world()
    await process_frame
    world.call("_render_party_from_snapshot", true)
    await process_frame
    _check(
        _count_character_queries(transport, "actor:premade-mira") == 2,
        "reopening Adventure refreshes cached Mira character data",
    )
    _check(
        _count_character_queries(transport, "actor:premade-aster") == 2,
        "reopening Adventure refreshes cached Aster character data",
    )

    var refreshed_aster_request := _last_character_query(transport, "actor:premade-aster")
    transport.queue_message(
        Protocol.make_response(
            "query.result",
            str(refreshed_aster_request["request_id"]),
            str(refreshed_aster_request["correlation_id"]),
            int(refreshed_aster_request["generation"]),
            false,
            {},
            Protocol.make_error(
                Protocol.ErrorCategory.VALIDATION,
                "Unknown created character",
                "actor record unavailable",
            ),
        )
    )
    await process_frame
    _check(
        _tree_text(party_cards).contains("Unknown created character"),
        "failed character queries render a user-visible party-card error",
    )
    var retry_button := _find_button_by_text(party_cards, "Retry character")
    _check(retry_button != null, "failed character queries expose a retry action")
    if retry_button != null:
        retry_button.pressed.emit()
        await process_frame
        _check(
            _count_character_queries(transport, "actor:premade-aster") == 3,
            "retry action resubmits the authoritative character query",
        )

    shell.shutdown()
    root.remove_child(shell)
    shell.queue_free()
    await process_frame


func _character_response(request: Dictionary, record: Dictionary) -> Dictionary:
    return Protocol.make_response(
        "query.result",
        str(request["request_id"]),
        str(request["correlation_id"]),
        int(request["generation"]),
        true,
        {"record": record},
    )


func _character_record(
    actor_id: String,
    name: String,
    class_name_value: String,
    hp: int,
    ac: int,
) -> Dictionary:
    return {
        "schema_version": 1,
        "catalog_id": "catalog:test",
        "species_id": "species:test",
        "background_id": "background:test",
        "class_id": "class:%s" % class_name_value,
        "ability_method_id": "ability:test",
        "appearance": {},
        "biography": "",
        "personality": "",
        "spell_ids": [],
        "feature_ids": [],
        "actor": {
            "schema_version": 1,
            "actor_id": actor_id,
            "name": name,
            "kind": "hero",
            "size": "medium",
            "level": 1,
            "proficiency_bonus": 2,
            "abilities": {},
            "hit_points": {"current": hp, "maximum": hp, "temporary": 0},
            "defense": {"armor_class": ac},
            "skills": [],
            "saves": [],
            "proficiencies": [],
            "movement": [],
            "senses": [],
            "inventory": [],
            "equipment": [],
            "resources": [],
            "conditions": [],
            "selected_options": [],
            "tags": [],
        },
    }


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
            "area": {
                "area_id": "area:reedhollow-square",
                "name": "Reedhollow Square",
                "tags": ["village"],
            },
            "party_ids": ["actor:premade-mira", "actor:premade-aster"],
            "flags": [],
            "quests": {"quest:test": "available"},
            "inventory": {"item:field-kit": 2},
            "equipped": {"actor:premade-mira|main_hand": "item:lantern-blade"},
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


func _last_character_query(transport, actor_id: String) -> Dictionary:
    for index in range(transport.sent_messages.size() - 1, -1, -1):
        var message: Dictionary = transport.sent_messages[index]
        if str(message.get("kind", "")) != "query.request":
            continue
        var payload: Dictionary = message.get("payload", {})
        if str(payload.get("query_type", "")) != "characters.get":
            continue
        var query: Dictionary = payload.get("query", {})
        if str(query.get("actor_id", "")) == actor_id:
            return message
    return {}


func _count_character_queries(transport, actor_id: String) -> int:
    var count := 0
    for message_value in transport.sent_messages:
        var message: Dictionary = message_value
        if str(message.get("kind", "")) != "query.request":
            continue
        var payload: Dictionary = message.get("payload", {})
        if str(payload.get("query_type", "")) != "characters.get":
            continue
        var query: Dictionary = payload.get("query", {})
        if str(query.get("actor_id", "")) == actor_id:
            count += 1
    return count


func _find_button_by_text(node: Node, text: String) -> Button:
    if node is Button and (node as Button).text == text:
        return node as Button
    for child in node.get_children():
        var found := _find_button_by_text(child, text)
        if found != null:
            return found
    return null


func _tree_text(node: Node) -> String:
    var lines: Array[String] = []
    if node is Label:
        lines.append((node as Label).text)
    elif node is RichTextLabel:
        lines.append((node as RichTextLabel).text)
    for child in node.get_children():
        lines.append(_tree_text(child))
    return "\n".join(lines)


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error(message)
