class_name WorldRPGView
extends CanvasLayer

signal close_requested()

var _state: ClientStateCoordinator
var _world_snapshot: Dictionary = {}
var _actions: Dictionary = {}
var _world_sequence := 0

@onready var _area: Label = %Area
@onready var _status: Label = %Status
@onready var _party_ids: LineEdit = %PartyIds
@onready var _start: Button = %StartCampaign
@onready var _refresh: Button = %Refresh
@onready var _travel: VBoxContainer = %Travel
@onready var _dialogue: VBoxContainer = %Dialogue
@onready var _interactions: VBoxContainer = %Interactions
@onready var _encounters: VBoxContainer = %Encounters
@onready var _shops: VBoxContainer = %Shops
@onready var _journal: RichTextLabel = %Journal
@onready var _close: Button = %Close


func _ready() -> void:
    visible = false
    _start.pressed.connect(_start_campaign)
    _refresh.pressed.connect(_refresh_world)
    _close.pressed.connect(func() -> void: close_requested.emit())


func bind_client_state(state: ClientStateCoordinator) -> void:
    if _state == state:
        return
    _unbind_state()
    _state = state
    if _state == null:
        return
    _state.query_completed.connect(_on_query_completed)
    _state.command_payload_received.connect(_on_command_payload)
    _state.command_completed.connect(_on_command_completed)


func show_world() -> void:
    visible = true
    _refresh_world()


func hide_world() -> void:
    visible = false


func world_snapshot() -> Dictionary:
    return _world_snapshot.duplicate(true)


func _refresh_world() -> void:
    if _state == null:
        return
    _state.request_query("world.snapshot", {}, "world:snapshot")
    _state.request_query("world.actions", {}, "world:actions")
    _state.request_query("world.journal", {}, "world:journal")


func _start_campaign() -> void:
    var ids: Array[String] = []
    for raw in _party_ids.text.split(",", false):
        var actor_id := raw.strip_edges()
        if not actor_id.is_empty():
            ids.append(actor_id)
    if ids.is_empty():
        _status.text = "Enter one or more actor IDs from the creator or loaded party."
        return
    _submit("world.start", {"party_ids": ids}, "world:start")


func _submit(command_type: String, payload: Dictionary, correlation_id: String) -> void:
    if _state == null:
        return
    var tactical_state := _state.authoritative.state_view()
    var command := {
        "command_id": "command:world-%d" % Time.get_ticks_msec(),
        "campaign_id": str(tactical_state.get("campaign_id", "campaign:local-dev")),
        "session_id": str(tactical_state.get("session_id", "session:local-dev")),
        "command_type": command_type,
        "payload": payload,
        "version": 1,
        "actor_id": null,
        "expected_sequence": _world_sequence,
    }
    _state.submit_command(command, correlation_id)


func _apply_snapshot(snapshot: Dictionary) -> void:
    _world_snapshot = snapshot.duplicate(true)
    var state_value: Variant = _world_snapshot.get("state", {})
    if typeof(state_value) != TYPE_DICTIONARY:
        return
    var world_state: Dictionary = state_value
    _world_sequence = int(world_state.get("sequence", 0))
    var area_value: Variant = world_state.get("area", {})
    if typeof(area_value) == TYPE_DICTIONARY:
        _area.text = str((area_value as Dictionary).get("name", "Unknown area"))
    var party_value: Variant = world_state.get("party_ids", [])
    _start.disabled = typeof(party_value) == TYPE_ARRAY and not (party_value as Array).is_empty()
    _render_state_summary(world_state)


func _render_state_summary(world_state: Dictionary) -> void:
    _status.text = "Currency: %d · World sequence: %d" % [
        int(world_state.get("currency", 0)),
        _world_sequence,
    ]


func _render_actions(payload: Dictionary) -> void:
    _actions = payload.duplicate(true)
    _clear(_travel)
    _clear(_dialogue)
    _clear(_interactions)
    _clear(_encounters)
    _clear(_shops)

    var travel_value: Variant = payload.get("travel", [])
    if typeof(travel_value) == TYPE_ARRAY:
        for row_value in travel_value:
            if typeof(row_value) != TYPE_DICTIONARY:
                continue
            var row: Dictionary = row_value
            var button := Button.new()
            button.text = "Travel: %s" % str(row.get("name", row.get("area_id", "")))
            var area_id := str(row.get("area_id", ""))
            button.pressed.connect(
                func() -> void:
                    _submit("world.travel", {"area_id": area_id}, "world:travel")
            )
            _travel.add_child(button)

    var dialogue_value: Variant = payload.get("dialogues", [])
    if typeof(dialogue_value) == TYPE_ARRAY:
        for row_value in dialogue_value:
            if typeof(row_value) != TYPE_DICTIONARY:
                continue
            var row: Dictionary = row_value
            var button := Button.new()
            button.text = "Talk: %s" % str(row.get("name", row.get("dialogue_id", "")))
            var dialogue_id := str(row.get("dialogue_id", ""))
            button.pressed.connect(
                func() -> void:
                    _submit("dialogue.start", {"dialogue_id": dialogue_id}, "world:dialogue-start")
            )
            _dialogue.add_child(button)

    var interactions_value: Variant = payload.get("interactions", [])
    if typeof(interactions_value) == TYPE_ARRAY:
        for row_value in interactions_value:
            if typeof(row_value) != TYPE_DICTIONARY:
                continue
            var row: Dictionary = row_value
            var button := Button.new()
            button.text = "%s · %s DC %d" % [
                str(row.get("name", "Interaction")),
                str(row.get("ability", "ability")).capitalize(),
                int(row.get("dc", 0)),
            ]
            var interaction_id := str(row.get("interaction_id", ""))
            button.pressed.connect(
                func() -> void:
                    _submit(
                        "world.resolve_interaction",
                        {"interaction_id": interaction_id},
                        "world:interaction",
                    )
            )
            _interactions.add_child(button)

    var encounters_value: Variant = payload.get("encounters", [])
    if typeof(encounters_value) == TYPE_ARRAY:
        for row_value in encounters_value:
            if typeof(row_value) != TYPE_DICTIONARY:
                continue
            var row: Dictionary = row_value
            var button := Button.new()
            button.text = "%s%s" % [
                "Boss victory: " if bool(row.get("boss", false)) else "Record tactical victory: ",
                str(row.get("name", row.get("encounter_id", ""))),
            ]
            button.disabled = not bool(row.get("available", false))
            var encounter_id := str(row.get("encounter_id", ""))
            button.pressed.connect(
                func() -> void:
                    _submit(
                        "world.complete_encounter",
                        {"encounter_id": encounter_id},
                        "world:encounter",
                    )
            )
            _encounters.add_child(button)

    var shops_value: Variant = payload.get("shops", [])
    if typeof(shops_value) == TYPE_ARRAY:
        for shop_value in shops_value:
            if typeof(shop_value) != TYPE_DICTIONARY:
                continue
            _render_shop(shop_value as Dictionary)

    var rest := Button.new()
    rest.text = "Rest"
    rest.disabled = not bool(payload.get("can_rest", false))
    rest.pressed.connect(func() -> void: _submit("world.rest", {}, "world:rest"))
    _interactions.add_child(rest)


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
        var button := Button.new()
        button.text = "Buy %s · %d" % [
            str(item.get("item_id", "item")),
            int(item.get("buy_price", 0)),
        ]
        var item_id := str(item.get("item_id", ""))
        button.pressed.connect(
            func() -> void:
                _submit(
                    "shop.buy",
                    {"shop_id": shop_id, "item_id": item_id, "quantity": 1},
                    "world:shop-buy",
                )
        )
        _shops.add_child(button)


func _render_journal(payload: Dictionary) -> void:
    var lines: Array[String] = []
    var quests_value: Variant = payload.get("quests", {})
    if typeof(quests_value) == TYPE_DICTIONARY:
        for quest_id in (quests_value as Dictionary).keys():
            lines.append("%s: %s" % [quest_id, (quests_value as Dictionary)[quest_id]])
    var entries_value: Variant = payload.get("entries", [])
    if typeof(entries_value) == TYPE_ARRAY:
        for entry in entries_value:
            lines.append(str(entry))
    _journal.text = "\n".join(lines)


func _request_dialogue() -> void:
    if _state != null:
        _state.request_query("dialogue.current", {}, "world:dialogue")


func _render_dialogue(payload: Dictionary) -> void:
    if not bool(payload.get("active", false)):
        return
    _clear(_dialogue)
    var text := Label.new()
    text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    text.text = "%s: %s" % [payload.get("speaker", ""), payload.get("text", "")]
    _dialogue.add_child(text)
    var choices_value: Variant = payload.get("choices", [])
    if typeof(choices_value) != TYPE_ARRAY:
        return
    for choice_value in choices_value:
        if typeof(choice_value) != TYPE_DICTIONARY:
            continue
        var choice: Dictionary = choice_value
        var button := Button.new()
        button.text = str(choice.get("text", choice.get("choice_id", "")))
        var choice_id := str(choice.get("choice_id", ""))
        button.pressed.connect(
            func() -> void:
                _submit("dialogue.choose", {"choice_id": choice_id}, "world:dialogue-choice")
        )
        _dialogue.add_child(button)


func _on_query_completed(correlation_id: String, _generation: int, payload: Dictionary) -> void:
    match correlation_id:
        "world:snapshot":
            var snapshot_value: Variant = payload.get("world_snapshot", {})
            if typeof(snapshot_value) == TYPE_DICTIONARY:
                _apply_snapshot(snapshot_value as Dictionary)
        "world:actions":
            _render_actions(payload)
        "world:journal":
            _render_journal(payload)
        "world:dialogue":
            _render_dialogue(payload)


func _on_command_payload(correlation_id: String, payload: Dictionary) -> void:
    if not correlation_id.begins_with("world:"):
        return
    var snapshot_value: Variant = payload.get("world_snapshot", {})
    if typeof(snapshot_value) == TYPE_DICTIONARY:
        _apply_snapshot(snapshot_value as Dictionary)
    _refresh_world()
    _request_dialogue()


func _on_command_completed(
    correlation_id: String,
    accepted: bool,
    user_message: String,
    debug_detail: String,
) -> void:
    if not correlation_id.begins_with("world:"):
        return
    if not accepted:
        _status.text = "%s · %s" % [user_message, debug_detail]


func _unbind_state() -> void:
    if _state == null:
        return
    if _state.query_completed.is_connected(_on_query_completed):
        _state.query_completed.disconnect(_on_query_completed)
    if _state.command_payload_received.is_connected(_on_command_payload):
        _state.command_payload_received.disconnect(_on_command_payload)
    if _state.command_completed.is_connected(_on_command_completed):
        _state.command_completed.disconnect(_on_command_completed)
    _state = null


func _clear(container: Node) -> void:
    for child in container.get_children():
        child.queue_free()
