extends "res://scenes/world/world_rpg_view.gd"

var _equipment_options: Dictionary = {}
var _legacy_equipment_fallback := false
var _equipment_query_pending := false

@onready var _save_load_panel: WorldSavePanel = %SaveLoad
@onready var _exploration_summary: Label = %ExplorationSummary
@onready var _equip_slot_options: OptionButton = %EquipSlotOptions
@onready var _credits: RichTextLabel = %Credits


func _ready() -> void:
    super._ready()
    _equip_item.item_selected.connect(_on_equipment_item_selected)
    _credits.text = (
        "[b]GodotDnDSimulator[/b]\n"
        + "Original v1.0 campaign: [i]Lanterns Below[/i].\n\n"
        + "The Godot client is presentation-only; authoritative rules, world state, "
        + "randomness, saves, and legality are resolved by the Python engine.\n\n"
        + "[b]Rules/content attribution[/b]\n"
        + "This repository can ingest approved, licensed SRD material and keeps source/license "
        + "provenance in its generated attribution bundle. The original Lanterns Below campaign "
        + "and its names, locations, dialogue, encounters, and items are project-original content.\n\n"
        + "Godot Engine is used under its own open-source license. Release builds must ship the "
        + "repository attribution/license bundle for every included third-party or licensed asset."
    )


func bind_client_state(state: ClientStateCoordinator) -> void:
    super.bind_client_state(state)
    _save_load_panel.bind_client_state(state)


func show_world() -> void:
    super.show_world()
    _save_load_panel.activate()


func _refresh_world() -> void:
    super._refresh_world()
    if _state == null:
        return
    _equipment_query_pending = true
    var request_id := _state.request_query(
        "inventory.equipment_options",
        {},
        "world:equipment-options",
    )
    if request_id.is_empty():
        _enable_legacy_equipment_fallback(
            "Equipment compatibility query is unavailable; enter an engine slot ID."
        )


func _apply_snapshot(snapshot: Dictionary) -> void:
    super._apply_snapshot(snapshot)
    _save_load_panel.set_world_snapshot(snapshot)


func _render_state_summary(world_state: Dictionary) -> void:
    super._render_state_summary(world_state)
    var flags_value: Variant = world_state.get("flags", [])
    if typeof(flags_value) == TYPE_ARRAY and (flags_value as Array).has("flag:campaign-complete"):
        _status.text += " · Campaign complete"


func _render_actions(payload: Dictionary) -> void:
    super._render_actions(payload)
    _render_exploration_summary(payload)
    _apply_action_availability(payload)
    _render_encounter_controls(payload)


func _render_exploration_summary(payload: Dictionary) -> void:
    var area_name := str(payload.get("area_name", payload.get("area_id", "Unknown area")))
    var tags_value: Variant = payload.get("area_tags", [])
    var tags: Array[String] = []
    if typeof(tags_value) == TYPE_ARRAY:
        for value in tags_value:
            tags.append(str(value))
    var tag_text := "" if tags.is_empty() else " · %s" % ", ".join(tags)
    _exploration_summary.text = "%s%s\n%s" % [
        area_name,
        tag_text,
        str(payload.get("exploration_prompt", "Choose an engine-provided action.")),
    ]


func _apply_action_availability(payload: Dictionary) -> void:
    var travel_value: Variant = payload.get("travel", [])
    if typeof(travel_value) == TYPE_ARRAY:
        var travel_rows: Array = travel_value
        var travel_buttons := _travel.get_children()
        for index in range(min(travel_rows.size(), travel_buttons.size())):
            if typeof(travel_rows[index]) != TYPE_DICTIONARY or not travel_buttons[index] is Button:
                continue
            var row: Dictionary = travel_rows[index]
            var button := travel_buttons[index] as Button
            button.disabled = not bool(row.get("available", true))
            button.tooltip_text = str(row.get("reason", ""))

    var interactions_value: Variant = payload.get("interactions", [])
    if typeof(interactions_value) == TYPE_ARRAY:
        var interaction_rows: Array = interactions_value
        var interaction_buttons := _interactions.get_children()
        for index in range(min(interaction_rows.size(), interaction_buttons.size())):
            if typeof(interaction_rows[index]) != TYPE_DICTIONARY or not interaction_buttons[index] is Button:
                continue
            var row: Dictionary = interaction_rows[index]
            var button := interaction_buttons[index] as Button
            button.disabled = not bool(row.get("available", true))
            button.tooltip_text = str(row.get("reason", ""))
        if interaction_buttons.size() > interaction_rows.size():
            var rest_control := interaction_buttons[interaction_rows.size()]
            if rest_control is Button:
                var rest := rest_control as Button
                rest.tooltip_text = str(payload.get("rest_reason", ""))


func _render_encounter_controls(payload: Dictionary) -> void:
    _clear(_encounters)
    var encounters_value: Variant = payload.get("encounters", [])
    if typeof(encounters_value) != TYPE_ARRAY:
        return
    for row_value in encounters_value:
        if typeof(row_value) != TYPE_DICTIONARY:
            continue
        var row: Dictionary = row_value
        var encounter_id := str(row.get("encounter_id", ""))
        var encounter_name := str(row.get("name", encounter_id))
        var active := bool(row.get("active", false))
        var available := bool(row.get("available", false))
        var button := Button.new()
        if active:
            button.text = "Record tactical victory: %s" % encounter_name
            button.tooltip_text = "Use after the active tactical battle has ended in a party victory."
            button.pressed.connect(
                func() -> void:
                    _submit(
                        "world.complete_encounter",
                        {"encounter_id": encounter_id},
                        "world:encounter-complete",
                    )
            )
        else:
            button.text = "%s%s" % [
                "Begin boss encounter: " if bool(row.get("boss", false)) else "Begin tactical encounter: ",
                encounter_name,
            ]
            button.disabled = not available
            button.tooltip_text = str(row.get("reason", ""))
            button.pressed.connect(
                func() -> void:
                    _submit(
                        "world.begin_encounter",
                        {"encounter_id": encounter_id},
                        "world:encounter-begin",
                    )
            )
        _encounters.add_child(button)


func _render_shop(shop: Dictionary) -> void:
    var heading := Label.new()
    heading.text = str(shop.get("name", "Shop"))
    _shops.add_child(heading)
    var shop_id := str(shop.get("shop_id", ""))
    var items_value: Variant = shop.get("items", [])
    if typeof(items_value) != TYPE_ARRAY:
        return
    for item_value in items_value:
        if typeof(item_value) != TYPE_DICTIONARY:
            continue
        var item: Dictionary = item_value
        var item_id := str(item.get("item_id", ""))
        var stock_value: Variant = item.get("stock")
        var stock_text := "∞" if stock_value == null else str(int(stock_value))
        var row := HBoxContainer.new()
        var label := Label.new()
        label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
        label.text = "%s · buy %d · sell %d · owned %d · stock %s" % [
            item_id,
            int(item.get("buy_price", 0)),
            int(item.get("sell_price", 0)),
            int(item.get("owned_quantity", 0)),
            stock_text,
        ]
        row.add_child(label)

        var buy := Button.new()
        buy.text = "Buy"
        buy.disabled = not bool(item.get("buy_available", true))
        buy.tooltip_text = str(item.get("buy_reason", ""))
        buy.pressed.connect(
            func() -> void:
                _submit(
                    "shop.buy",
                    {"shop_id": shop_id, "item_id": item_id, "quantity": 1},
                    "world:shop-buy",
                )
        )
        row.add_child(buy)

        var sell := Button.new()
        sell.text = "Sell"
        sell.disabled = not bool(item.get("sell_available", false))
        sell.tooltip_text = str(item.get("sell_reason", ""))
        sell.pressed.connect(
            func() -> void:
                _submit(
                    "shop.sell",
                    {"shop_id": shop_id, "item_id": item_id, "quantity": 1},
                    "world:shop-sell",
                )
        )
        row.add_child(sell)
        _shops.add_child(row)


func _refresh_equip_controls(world_state: Dictionary) -> void:
    if _legacy_equipment_fallback:
        super._refresh_equip_controls(world_state)
        _equip_slot.visible = true
        _equip_slot_options.visible = false
        return

    if _equipment_options.is_empty():
        super._refresh_equip_controls(world_state)
        _equip_slot.visible = false
        _equip_slot_options.visible = true
        _equip_slot_options.clear()
        _equip.disabled = true
        return

    _equip_slot.visible = false
    _equip_slot_options.visible = true
    _equip_actor.clear()
    _equip_item.clear()
    _equip_slot_options.clear()

    var party_value: Variant = _equipment_options.get(
        "party_ids",
        world_state.get("party_ids", []),
    )
    if typeof(party_value) == TYPE_ARRAY:
        for actor_value in party_value:
            var actor_id := str(actor_value)
            _equip_actor.add_item(actor_id)
            _equip_actor.set_item_metadata(_equip_actor.item_count - 1, actor_id)

    var items_value: Variant = _equipment_options.get("items", [])
    if typeof(items_value) == TYPE_ARRAY:
        for item_value in items_value:
            if typeof(item_value) != TYPE_DICTIONARY:
                continue
            var item: Dictionary = item_value
            var item_id := str(item.get("item_id", ""))
            _equip_item.add_item("%s × %d" % [item_id, int(item.get("quantity", 0))])
            _equip_item.set_item_metadata(_equip_item.item_count - 1, item_id)

    _refresh_slot_choices()


func _on_equipment_item_selected(_index: int) -> void:
    if not _legacy_equipment_fallback and not _equipment_options.is_empty():
        _refresh_slot_choices()


func _refresh_slot_choices() -> void:
    _equip_slot_options.clear()
    if _equip_item.item_count == 0:
        _equip.disabled = true
        return
    var selected_item_id := str(_equip_item.get_item_metadata(_equip_item.selected))
    var items_value: Variant = _equipment_options.get("items", [])
    if typeof(items_value) == TYPE_ARRAY:
        for item_value in items_value:
            if typeof(item_value) != TYPE_DICTIONARY:
                continue
            var item: Dictionary = item_value
            if str(item.get("item_id", "")) != selected_item_id:
                continue
            var slots_value: Variant = item.get("slots", [])
            if typeof(slots_value) != TYPE_ARRAY:
                break
            for slot_value in slots_value:
                if typeof(slot_value) != TYPE_DICTIONARY:
                    continue
                var slot: Dictionary = slot_value
                var slot_id := str(slot.get("slot_id", ""))
                _equip_slot_options.add_item(str(slot.get("label", slot_id)))
                _equip_slot_options.set_item_metadata(
                    _equip_slot_options.item_count - 1,
                    slot_id,
                )
            break
    _equip.disabled = (
        _equip_actor.item_count == 0
        or _equip_item.item_count == 0
        or _equip_slot_options.item_count == 0
    )


func _equip_selected() -> void:
    if _equip_actor.item_count == 0 or _equip_item.item_count == 0:
        _status.text = "No authoritative actor/item equipment choice is available."
        return
    var actor_id := str(_equip_actor.get_item_metadata(_equip_actor.selected))
    var item_id := str(_equip_item.get_item_metadata(_equip_item.selected))
    var slot_id := ""
    if _legacy_equipment_fallback:
        slot_id = _equip_slot.text.strip_edges()
    elif _equip_slot_options.item_count > 0:
        slot_id = str(_equip_slot_options.get_item_metadata(_equip_slot_options.selected))
    if slot_id.is_empty():
        _status.text = "No engine-approved equipment slot is available."
        return
    _submit(
        "inventory.equip",
        {"actor_id": actor_id, "slot": slot_id, "item_id": item_id},
        "world:equip",
    )


func _on_query_completed(
    correlation_id: String,
    generation: int,
    payload: Dictionary,
) -> void:
    if correlation_id == "world:equipment-options":
        _equipment_query_pending = false
        _legacy_equipment_fallback = false
        _equip_slot.visible = false
        _equip_slot_options.visible = true
        _equipment_options = payload.duplicate(true)
        var state_value: Variant = _world_snapshot.get("state", {})
        if typeof(state_value) == TYPE_DICTIONARY:
            _refresh_equip_controls(state_value as Dictionary)
        return
    super._on_query_completed(correlation_id, generation, payload)


func _on_query_failed(
    correlation_id: String,
    generation: int,
    user_message: String,
    debug_detail: String,
) -> void:
    if correlation_id == "world:equipment-options":
        _equipment_query_pending = false
        _enable_legacy_equipment_fallback(
            "Equipment compatibility choices are unavailable on this engine; enter an engine slot ID."
        )
        return
    super._on_query_failed(correlation_id, generation, user_message, debug_detail)


func _enable_legacy_equipment_fallback(message: String) -> void:
    _equipment_options.clear()
    _legacy_equipment_fallback = true
    _equip_slot.visible = true
    _equip_slot_options.visible = false
    var state_value: Variant = _world_snapshot.get("state", {})
    if typeof(state_value) == TYPE_DICTIONARY:
        super._refresh_equip_controls(state_value as Dictionary)
    _status.text = message
