class_name WorldSavePanel
extends VBoxContainer

var _state: ClientStateCoordinator
var _store: WorldSaveStore
var _world_snapshot: Dictionary = {}
var _slots: Dictionary = {}
var _save_query_slot := ""
var _load_file_slot := ""
var _load_command_slot := ""

@onready var _slot: OptionButton = %SaveSlot
@onready var _details: Label = %SaveDetails
@onready var _save: Button = %SaveGame
@onready var _load: Button = %LoadGame
@onready var _refresh: Button = %RefreshSaves
@onready var _status: Label = %SaveStatus


func _ready() -> void:
    for slot_id_value in WorldSaveStore.slot_ids():
        var slot_id := str(slot_id_value)
        _slot.add_item(WorldSaveStore.slot_label(slot_id))
        _slot.set_item_metadata(_slot.item_count - 1, slot_id)
    _slot.item_selected.connect(_on_slot_selected)
    _save.pressed.connect(_save_selected_slot)
    _load.pressed.connect(_load_selected_slot)
    _refresh.pressed.connect(_refresh_slots)
    bind_save_store(WorldSaveStore.new())
    _refresh_slot_labels()
    _update_controls()


func bind_client_state(state: ClientStateCoordinator) -> void:
    if _state == state:
        return
    _unbind_client_state()
    _state = state
    if _state != null:
        _state.query_completed.connect(_on_query_completed)
        _state.query_failed.connect(_on_query_failed)
        _state.command_completed.connect(_on_command_completed)
        _state.bridge_disconnected.connect(_on_bridge_disconnected)
        _state.bridge_unbound.connect(_on_bridge_unbound)
    _update_controls()


func bind_save_store(store: WorldSaveStore) -> void:
    if _store == store:
        return
    _unbind_save_store()
    _store = store
    if _store != null:
        _store.busy_changed.connect(_on_store_busy_changed)
        _store.save_completed.connect(_on_store_save_completed)
        _store.load_completed.connect(_on_store_load_completed)
        _store.slots_listed.connect(_on_store_slots_listed)
        _store.operation_failed.connect(_on_store_operation_failed)
    _update_controls()


func set_world_snapshot(snapshot: Dictionary) -> void:
    _world_snapshot = snapshot.duplicate(true)
    _update_controls()


func activate() -> void:
    _refresh_slots()


func _save_selected_slot() -> void:
    var slot_id := _selected_slot_id()
    if _state == null:
        _status.text = "The engine bridge is not available."
        return
    if _world_snapshot.is_empty():
        _status.text = "Start or load a campaign before saving."
        return
    if _operation_in_progress():
        _status.text = "Finish the current save operation first."
        return
    var correlation_id := _save_correlation(slot_id)
    _save_query_slot = slot_id
    var request_id := _state.request_query(
        "world.save",
        {"encoding": "lossless-json"},
        correlation_id,
    )
    if request_id.is_empty():
        _save_query_slot = ""
        _status.text = "The authoritative save snapshot request could not be submitted."
    else:
        _status.text = "Requesting authoritative snapshot for %s…" % WorldSaveStore.slot_label(slot_id)
    _update_controls()


func _load_selected_slot() -> void:
    var slot_id := _selected_slot_id()
    if _state == null or _store == null:
        _status.text = "Save/load is not available."
        return
    if _operation_in_progress():
        _status.text = "Finish the current save operation first."
        return
    var info: Dictionary = _slots.get(slot_id, {})
    if not bool(info.get("exists", false)) or info.has("error"):
        _status.text = "The selected slot does not contain a readable save."
        return
    _load_file_slot = slot_id
    if _store.load_slot(slot_id):
        _status.text = "Reading %s…" % WorldSaveStore.slot_label(slot_id)
    else:
        _load_file_slot = ""
    _update_controls()


func _refresh_slots() -> void:
    if _store == null or _store.is_busy() or not _save_query_slot.is_empty() or not _load_command_slot.is_empty():
        return
    if not _store.list_slots():
        return
    _status.text = "Checking save slots…"
    _update_controls()


func _on_query_completed(
    correlation_id: String,
    _generation: int,
    payload: Dictionary,
) -> void:
    if _save_query_slot.is_empty() or correlation_id != _save_correlation(_save_query_slot):
        return
    var slot_id := _save_query_slot
    _save_query_slot = ""
    var snapshot_value: Variant = payload.get("world_snapshot_json", "")
    if typeof(snapshot_value) != TYPE_STRING or str(snapshot_value).strip_edges().is_empty():
        _status.text = "The engine did not return a lossless world snapshot."
        _update_controls()
        return
    var metadata_value: Variant = payload.get("save_metadata", null)
    if typeof(metadata_value) != TYPE_DICTIONARY:
        _status.text = "The engine did not return valid save metadata."
        _update_controls()
        return
    if _store == null:
        _status.text = "The local save store is unavailable."
        _update_controls()
        return
    var metadata := (metadata_value as Dictionary).duplicate(true)
    metadata["saved_at"] = Time.get_datetime_string_from_system(false, true)
    if _store.save_slot(slot_id, str(snapshot_value), metadata):
        _status.text = "Writing %s…" % WorldSaveStore.slot_label(slot_id)
    _update_controls()


func _on_query_failed(
    correlation_id: String,
    _generation: int,
    user_message: String,
    debug_detail: String,
) -> void:
    if _save_query_slot.is_empty() or correlation_id != _save_correlation(_save_query_slot):
        return
    _save_query_slot = ""
    _status.text = _failure_text("Save snapshot request failed", user_message, debug_detail)
    _update_controls()


func _on_store_save_completed(slot_id: String, metadata: Dictionary) -> void:
    _slots[slot_id] = {
        "exists": true,
        "metadata": metadata.duplicate(true),
        "recovered_backup": false,
    }
    _status.text = "%s saved." % WorldSaveStore.slot_label(slot_id)
    _refresh_slot_labels()
    _update_controls()


func _on_store_load_completed(
    slot_id: String,
    world_snapshot_json: String,
    _metadata: Dictionary,
) -> void:
    if slot_id != _load_file_slot:
        return
    _load_file_slot = ""
    if _state == null:
        _status.text = "The engine bridge disconnected before the save could be validated."
        _update_controls()
        return
    var state_value: Variant = _world_snapshot.get("state", {})
    if typeof(state_value) != TYPE_DICTIONARY:
        _status.text = "The active world sequence is unavailable; refresh before loading."
        _update_controls()
        return
    var expected_sequence := int((state_value as Dictionary).get("sequence", 0))
    var tactical_state := _state.authoritative.state_view()
    var command := {
        "command_id": "command:world-load-%d" % Time.get_ticks_msec(),
        "campaign_id": str(tactical_state.get("campaign_id", "campaign:local-dev")),
        "session_id": str(tactical_state.get("session_id", "session:local-dev")),
        "command_type": "world.load",
        "payload": {"world_snapshot_json": world_snapshot_json},
        "version": 1,
        "actor_id": null,
        "expected_sequence": expected_sequence,
    }
    var correlation_id := _load_correlation(slot_id)
    _load_command_slot = slot_id
    var request_id := _state.submit_command(command, correlation_id)
    if request_id.is_empty():
        _load_command_slot = ""
        _status.text = "The loaded snapshot could not be submitted for authoritative validation."
    else:
        _status.text = "Validating %s with the engine…" % WorldSaveStore.slot_label(slot_id)
    _update_controls()


func _on_command_completed(
    correlation_id: String,
    accepted: bool,
    user_message: String,
    debug_detail: String,
) -> void:
    if _load_command_slot.is_empty() or correlation_id != _load_correlation(_load_command_slot):
        return
    var slot_id := _load_command_slot
    _load_command_slot = ""
    if accepted:
        _status.text = "%s loaded and validated." % WorldSaveStore.slot_label(slot_id)
    else:
        _status.text = _failure_text("Load rejected", user_message, debug_detail)
    _update_controls()


func _on_bridge_disconnected(reason: String) -> void:
    _reset_network_operation(
        "Engine connection lost; pending save/load request cleared. %s" % reason
    )


func _on_bridge_unbound() -> void:
    _reset_network_operation("Engine bridge is reconnecting; pending save/load request cleared.")


func _reset_network_operation(message: String) -> void:
    var had_network_operation := (
        not _save_query_slot.is_empty() or not _load_command_slot.is_empty()
    )
    _save_query_slot = ""
    _load_command_slot = ""
    if had_network_operation:
        _status.text = message
    _update_controls()


func _on_store_slots_listed(slots: Dictionary) -> void:
    _slots = slots.duplicate(true)
    _refresh_slot_labels()
    _status.text = "Save slots ready."
    _update_controls()


func _on_store_operation_failed(
    operation: String,
    slot_id: String,
    user_message: String,
    debug_detail: String,
) -> void:
    if operation == "load" and slot_id == _load_file_slot:
        _load_file_slot = ""
    _status.text = _failure_text("Save/load operation failed", user_message, debug_detail)
    _update_controls()


func _on_store_busy_changed(_busy: bool) -> void:
    _update_controls()


func _on_slot_selected(_index: int) -> void:
    _refresh_slot_details()
    _update_controls()


func _refresh_slot_labels() -> void:
    for index in range(_slot.item_count):
        var slot_id := str(_slot.get_item_metadata(index))
        var label := WorldSaveStore.slot_label(slot_id)
        if not _slots.has(slot_id):
            label += " · checking"
        else:
            var info: Dictionary = _slots[slot_id]
            if info.has("error"):
                label += " · unreadable"
            elif not bool(info.get("exists", false)):
                label += " · empty"
            else:
                var metadata_value: Variant = info.get("metadata", {})
                var metadata := metadata_value as Dictionary if typeof(metadata_value) == TYPE_DICTIONARY else {}
                var area_name := str(metadata.get("area_name", "Unknown area"))
                var sequence := int(metadata.get("sequence", 0))
                label += " · %s · seq %d" % [area_name, sequence]
        _slot.set_item_text(index, label)
    _refresh_slot_details()


func _refresh_slot_details() -> void:
    var slot_id := _selected_slot_id()
    if not _slots.has(slot_id):
        _details.text = "Save metadata has not been loaded yet."
        return
    var info: Dictionary = _slots[slot_id]
    if info.has("error"):
        _details.text = "Unreadable save: %s" % str(info.get("error", "unknown error"))
        return
    if not bool(info.get("exists", false)):
        _details.text = "Empty slot."
        return
    var metadata_value: Variant = info.get("metadata", {})
    var metadata := metadata_value as Dictionary if typeof(metadata_value) == TYPE_DICTIONARY else {}
    var saved_at := str(metadata.get("saved_at", "unknown time"))
    var area_name := str(metadata.get("area_name", "Unknown area"))
    var sequence := int(metadata.get("sequence", 0))
    var recovery := " · recovered backup" if bool(info.get("recovered_backup", false)) else ""
    _details.text = "%s · %s · world sequence %d%s" % [saved_at, area_name, sequence, recovery]


func _update_controls() -> void:
    if not is_node_ready():
        return
    var busy := _operation_in_progress()
    _slot.disabled = busy
    _refresh.disabled = busy or _store == null
    _save.disabled = busy or _state == null or _world_snapshot.is_empty() or _store == null
    var slot_id := _selected_slot_id()
    var info: Dictionary = _slots.get(slot_id, {})
    var readable := bool(info.get("exists", false)) and not info.has("error")
    _load.disabled = busy or _state == null or _store == null or not readable


func _operation_in_progress() -> bool:
    return (
        (_store != null and _store.is_busy())
        or not _save_query_slot.is_empty()
        or not _load_file_slot.is_empty()
        or not _load_command_slot.is_empty()
    )


func _selected_slot_id() -> String:
    if not is_node_ready() or _slot.item_count == 0:
        return "slot-1"
    return str(_slot.get_item_metadata(_slot.selected))


static func _save_correlation(slot_id: String) -> String:
    return "world:save-file:%s" % slot_id


static func _load_correlation(slot_id: String) -> String:
    return "world:load-file:%s" % slot_id


static func _failure_text(prefix: String, user_message: String, debug_detail: String) -> String:
    var message := user_message.strip_edges()
    if message.is_empty():
        message = debug_detail.strip_edges()
    if message.is_empty():
        message = "unknown error"
    return "%s: %s" % [prefix, message]


func _unbind_client_state() -> void:
    if _state == null:
        return
    if _state.query_completed.is_connected(_on_query_completed):
        _state.query_completed.disconnect(_on_query_completed)
    if _state.query_failed.is_connected(_on_query_failed):
        _state.query_failed.disconnect(_on_query_failed)
    if _state.command_completed.is_connected(_on_command_completed):
        _state.command_completed.disconnect(_on_command_completed)
    if _state.bridge_disconnected.is_connected(_on_bridge_disconnected):
        _state.bridge_disconnected.disconnect(_on_bridge_disconnected)
    if _state.bridge_unbound.is_connected(_on_bridge_unbound):
        _state.bridge_unbound.disconnect(_on_bridge_unbound)
    _state = null


func _unbind_save_store() -> void:
    if _store == null:
        return
    if _store.busy_changed.is_connected(_on_store_busy_changed):
        _store.busy_changed.disconnect(_on_store_busy_changed)
    if _store.save_completed.is_connected(_on_store_save_completed):
        _store.save_completed.disconnect(_on_store_save_completed)
    if _store.load_completed.is_connected(_on_store_load_completed):
        _store.load_completed.disconnect(_on_store_load_completed)
    if _store.slots_listed.is_connected(_on_store_slots_listed):
        _store.slots_listed.disconnect(_on_store_slots_listed)
    if _store.operation_failed.is_connected(_on_store_operation_failed):
        _store.operation_failed.disconnect(_on_store_operation_failed)
    _store = null
