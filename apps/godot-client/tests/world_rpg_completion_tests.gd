extends SceneTree

const Protocol = preload("res://bridge/bridge_protocol.gd")
const EngineBridgeScript = preload("res://bridge/engine_bridge.gd")
const FakeTransportScript = preload("res://bridge/fake_engine_transport.gd")
const CoordinatorScript = preload("res://state/client_state_coordinator.gd")

var _failures := 0


func _initialize() -> void:
    call_deferred("_run")


func _run() -> void:
    await _test_completed_world_client_surfaces()
    if _failures == 0:
        print("Godot v1 RPG completion tests: PASS")
        quit(0)
    push_error("Godot v1 RPG completion tests: %d failure(s)" % _failures)
    quit(1)


func _test_completed_world_client_surfaces() -> void:
    var scene := load("res://scenes/world/world_rpg_view.tscn") as PackedScene
    _check(scene != null, "completed Adventure scene loads")
    if scene == null:
        return
    var world = scene.instantiate()
    root.add_child(world)
    await process_frame

    var bridge = EngineBridgeScript.new()
    var transport = FakeTransportScript.new()
    var coordinator = CoordinatorScript.new()
    coordinator.bind_bridge(bridge)
    _check(bridge.initialize(transport) == OK, "completion bridge initializes")
    var hello := _last_message(transport, "bridge.hello")
    _check(not hello.is_empty(), "completion bridge sends hello")
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
                    "world.runtime.v1",
                    "world.commands.v1",
                    "world.queries.v1",
                    "inventory.equipment-options.v1",
                    "shops.v1",
                ],
            },
        )
    )
    bridge.poll(0.0)
    coordinator.authoritative.ingest_snapshot(_core_snapshot())
    world.call("bind_client_state", coordinator)
    world.call("_apply_snapshot", _world_snapshot())

    world.call("_refresh_world")
    var equipment_request := _last_query(transport, "inventory.equipment_options")
    _check(
        not equipment_request.is_empty(),
        "Adventure requests engine-owned equipment compatibility choices",
    )
    if not equipment_request.is_empty():
        transport.queue_message(
            Protocol.make_response(
                "query.result",
                str(equipment_request["request_id"]),
                str(equipment_request["correlation_id"]),
                int(equipment_request["generation"]),
                true,
                {
                    "party_ids": ["actor:premade-mira"],
                    "items": [
                        {
                            "item_id": "item:rope-coil",
                            "quantity": 1,
                            "slots": [
                                {"slot_id": "slot:utility", "label": "Utility"},
                            ],
                        },
                    ],
                },
            )
        )
        bridge.poll(0.0)

    var actions := {
        "area_id": "area:market-row",
        "area_name": "Market Row",
        "area_tags": ["village", "shop"],
        "exploration_prompt": "Choose a destination, conversation, interaction, rest, shop action, or encounter.",
        "travel": [
            {
                "area_id": "area:reedhollow-square",
                "name": "Reedhollow Square",
                "available": false,
                "reason": "Finish the active dialogue first.",
            },
        ],
        "dialogues": [],
        "interactions": [
            {
                "interaction_id": "interaction:test",
                "name": "Inspect the stall",
                "ability": "wisdom",
                "dc": 10,
                "completed": true,
                "available": false,
                "reason": "Already completed.",
            },
        ],
        "encounters": [
            {
                "encounter_id": "encounter:test",
                "name": "Market Trouble",
                "boss": false,
                "available": true,
                "active": false,
                "reason": "",
            },
        ],
        "shops": [
            {
                "shop_id": "shop:test",
                "name": "Test Supplies",
                "items": [
                    {
                        "item_id": "item:rope-coil",
                        "buy_price": 5,
                        "sell_price": 2,
                        "stock": 2,
                        "owned_quantity": 1,
                        "buy_available": true,
                        "buy_reason": "",
                        "sell_available": true,
                        "sell_reason": "",
                    },
                ],
            },
        ],
        "can_rest": false,
        "rest_reason": "Finish the active dialogue first.",
    }
    world.call("_render_actions", actions)

    var summary: Label = world.get_node("Panel/Margin/VBox/ExplorationSummary")
    _check(summary.text.contains("Market Row"), "exploration HUD shows authoritative area name")
    _check(summary.text.contains("village"), "exploration HUD shows authoritative area tags")
    _check(summary.text.contains("Choose a destination"), "exploration HUD shows engine prompt")

    var travel_box: VBoxContainer = world.get_node(
        "Panel/Margin/VBox/Columns/ActionsScroll/Actions/Travel"
    )
    _check(travel_box.get_child_count() == 1, "travel control renders")
    if travel_box.get_child_count() == 1:
        var travel_button := travel_box.get_child(0) as Button
        _check(travel_button.disabled, "travel availability comes from engine descriptor")
        _check(
            travel_button.tooltip_text.contains("active dialogue"),
            "travel rejection reason is presented",
        )

    var interactions: VBoxContainer = world.get_node(
        "Panel/Margin/VBox/Columns/ActionsScroll/Actions/Interactions"
    )
    _check(interactions.get_child_count() >= 2, "interaction and rest controls render")
    if interactions.get_child_count() >= 2:
        var interaction_button := interactions.get_child(0) as Button
        var rest_button := interactions.get_child(interactions.get_child_count() - 1) as Button
        _check(interaction_button.disabled, "completed interaction is disabled by engine data")
        _check(rest_button.disabled, "rest availability is authoritative")
        _check(rest_button.tooltip_text.contains("active dialogue"), "rest reason is visible")

    var shops: VBoxContainer = world.get_node(
        "Panel/Margin/VBox/Columns/ActionsScroll/Actions/Shops"
    )
    var sell_button := _find_button_by_text(shops, "Sell")
    _check(sell_button != null, "shop UI exposes Sell alongside Buy")
    if sell_button != null:
        _check(not sell_button.disabled, "sell button follows authoritative ownership state")
        sell_button.pressed.emit()
        await process_frame
        var sell_message := _last_command(transport, "shop.sell")
        _check(not sell_message.is_empty(), "Sell routes through authoritative shop.sell")
        if not sell_message.is_empty():
            var command: Dictionary = (sell_message.get("payload", {}) as Dictionary).get("command", {})
            var intent: Dictionary = command.get("payload", {})
            _check(str(intent.get("item_id", "")) == "item:rope-coil", "sell intent uses engine item ID")

    var slot_options: OptionButton = world.get_node(
        "Panel/Margin/VBox/Columns/ManagementTabs/Inventory/EquipRow/EquipSlotOptions"
    )
    var legacy_slot: LineEdit = world.get_node(
        "Panel/Margin/VBox/Columns/ManagementTabs/Inventory/EquipRow/EquipSlot"
    )
    _check(not legacy_slot.visible, "free-text equipment slot control is no longer user-facing")
    _check(slot_options.item_count == 1, "engine equipment query supplies slot dropdown")
    if slot_options.item_count == 1:
        _check(
            str(slot_options.get_item_metadata(0)) == "slot:utility",
            "slot dropdown preserves authoritative slot ID",
        )
    var equip_button: Button = world.get_node(
        "Panel/Margin/VBox/Columns/ManagementTabs/Inventory/EquipRow/Equip"
    )
    _check(not equip_button.disabled, "valid engine-approved equipment choice is actionable")
    equip_button.pressed.emit()
    await process_frame
    var equip_message := _last_command(transport, "inventory.equip")
    _check(not equip_message.is_empty(), "equipment dropdown routes inventory.equip")
    if not equip_message.is_empty():
        var equip_command: Dictionary = (equip_message.get("payload", {}) as Dictionary).get("command", {})
        var equip_intent: Dictionary = equip_command.get("payload", {})
        _check(
            str(equip_intent.get("slot", "")) == "slot:utility",
            "equipment command uses exact engine-approved slot",
        )

    var encounters: VBoxContainer = world.get_node(
        "Panel/Margin/VBox/Columns/ActionsScroll/Actions/Encounters"
    )
    var begin_button := _find_button_containing(encounters, "Begin tactical encounter")
    _check(begin_button != null, "available world encounter exposes Begin tactical encounter")
    if begin_button != null:
        begin_button.pressed.emit()
        await process_frame
        _check(
            not _last_command(transport, "world.begin_encounter").is_empty(),
            "encounter launch routes through world.begin_encounter",
        )

    var active_actions := actions.duplicate(true)
    active_actions["encounters"] = [
        {
            "encounter_id": "encounter:test",
            "name": "Market Trouble",
            "boss": false,
            "available": false,
            "active": true,
            "reason": "Tactical encounter is already active.",
        },
    ]
    world.call("_render_actions", active_actions)
    var complete_button := _find_button_containing(encounters, "Record tactical victory")
    _check(complete_button != null, "active encounter exposes authoritative completion intent")
    if complete_button != null:
        complete_button.pressed.emit()
        await process_frame
        _check(
            not _last_command(transport, "world.complete_encounter").is_empty(),
            "active encounter completion routes through world.complete_encounter",
        )

    var credits: RichTextLabel = world.get_node(
        "Panel/Margin/VBox/Columns/ManagementTabs/Credits"
    )
    _check(credits.text.contains("Lanterns Below"), "credits identify original campaign")
    _check(credits.text.contains("Rules/content attribution"), "credits expose attribution guidance")

    bridge.shutdown()
    root.remove_child(world)
    world.queue_free()
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


func _world_snapshot() -> Dictionary:
    return {
        "schema_version": 1,
        "state": {
            "campaign_id": "campaign:test",
            "sequence": 7,
            "mode": "world",
            "area": {
                "area_id": "area:market-row",
                "name": "Market Row",
                "tags": ["village", "shop"],
            },
            "party_ids": ["actor:premade-mira"],
            "flags": [],
            "quests": {"quest:lanterns-below": "active"},
            "inventory": {"item:rope-coil": 1},
            "equipped": {},
            "shop_stock": {"shop:test|item:rope-coil": 2},
            "currency": 20,
            "active_dialogue": null,
            "completed_interactions": [],
            "completed_encounters": [],
            "journal": [],
            "rest_count": 0,
        },
        "rng_initial": {"algorithm": "pcg32-v1", "state": 1, "increment": 3},
        "rng": {"algorithm": "pcg32-v1", "state": 1, "increment": 3},
        "events": [],
    }


func _last_query(transport, query_type: String) -> Dictionary:
    for index in range(transport.sent_messages.size() - 1, -1, -1):
        var message: Dictionary = transport.sent_messages[index]
        if str(message.get("kind", "")) != "query.request":
            continue
        var payload: Dictionary = message.get("payload", {})
        if str(payload.get("query_type", "")) == query_type:
            return message
    return {}


func _last_command(transport, command_type: String) -> Dictionary:
    for index in range(transport.sent_messages.size() - 1, -1, -1):
        var message: Dictionary = transport.sent_messages[index]
        if str(message.get("kind", "")) != "command.submit":
            continue
        var payload: Dictionary = message.get("payload", {})
        var command: Dictionary = payload.get("command", {})
        if str(command.get("command_type", "")) == command_type:
            return message
    return {}


func _last_message(transport, kind: String) -> Dictionary:
    for index in range(transport.sent_messages.size() - 1, -1, -1):
        var message: Dictionary = transport.sent_messages[index]
        if str(message.get("kind", "")) == kind:
            return message
    return {}


func _find_button_by_text(node: Node, text: String) -> Button:
    for child in node.get_children():
        if child is Button and (child as Button).text == text:
            return child as Button
        var nested := _find_button_by_text(child, text)
        if nested != null:
            return nested
    return null


func _find_button_containing(node: Node, text: String) -> Button:
    for child in node.get_children():
        if child is Button and (child as Button).text.contains(text):
            return child as Button
        var nested := _find_button_containing(child, text)
        if nested != null:
            return nested
    return null


func _check(condition: bool, message: String) -> void:
    if condition:
        return
    _failures += 1
    push_error(message)
