class_name WorldSaveStore
extends RefCounted

signal busy_changed(busy: bool)
signal save_completed(slot_id: String, metadata: Dictionary)
signal load_completed(slot_id: String, world_snapshot_json: String, metadata: Dictionary)
signal slots_listed(slots: Dictionary)
signal operation_failed(
    operation: String,
    slot_id: String,
    user_message: String,
    debug_detail: String,
)

const FORMAT_ID := "godot-dnd-world-save"
const FORMAT_VERSION := 1
const MAX_SAVE_BYTES := 1_048_576
const DEFAULT_ROOT := "user://saves/world"
const SLOT_IDS := PackedStringArray(["slot-1", "slot-2", "slot-3"])
const SLOT_LABELS := {
    "slot-1": "Slot 1",
    "slot-2": "Slot 2",
    "slot-3": "Slot 3",
}

var _root_dir: String
var _root_absolute: String
var _thread: Thread
var _busy := false


func _init(root_dir: String = DEFAULT_ROOT) -> void:
    _root_dir = root_dir.trim_suffix("/")
    _root_absolute = ProjectSettings.globalize_path(_root_dir)


static func slot_ids() -> PackedStringArray:
    return SLOT_IDS.duplicate()


static func slot_label(slot_id: String) -> String:
    return str(SLOT_LABELS.get(slot_id, slot_id))


func is_busy() -> bool:
    return _busy


func save_slot(
    slot_id: String,
    world_snapshot_json: String,
    metadata: Dictionary = {},
) -> bool:
    if not _validate_slot(slot_id, "save"):
        return false
    if world_snapshot_json.strip_edges().is_empty():
        operation_failed.emit(
            "save",
            slot_id,
            "There is no authoritative world state to save.",
            "world_snapshot_json is empty",
        )
        return false
    var envelope := {
        "format": FORMAT_ID,
        "format_version": FORMAT_VERSION,
        "slot_id": slot_id,
        "metadata": metadata.duplicate(true),
        "world_snapshot_json": world_snapshot_json,
    }
    return _start_operation(
        "save",
        slot_id,
        Callable(self, "_save_worker").bind(slot_id, envelope),
    )


func load_slot(slot_id: String) -> bool:
    if not _validate_slot(slot_id, "load"):
        return false
    return _start_operation(
        "load",
        slot_id,
        Callable(self, "_load_worker").bind(slot_id),
    )


func list_slots() -> bool:
    return _start_operation(
        "list",
        "",
        Callable(self, "_list_worker"),
    )


func _validate_slot(slot_id: String, operation: String) -> bool:
    if SLOT_IDS.has(slot_id):
        return true
    operation_failed.emit(
        operation,
        slot_id,
        "That save slot is not available.",
        "unsupported slot_id=%s" % slot_id,
    )
    return false


func _start_operation(
    operation: String,
    slot_id: String,
    worker: Callable,
) -> bool:
    if _busy:
        operation_failed.emit(
            operation,
            slot_id,
            "Another save operation is already in progress.",
            "WorldSaveStore allows one disk operation at a time",
        )
        return false
    _busy = true
    busy_changed.emit(true)
    _thread = Thread.new()
    var error := _thread.start(worker, Thread.PRIORITY_LOW)
    if error == OK:
        return true
    _thread = null
    _busy = false
    busy_changed.emit(false)
    operation_failed.emit(
        operation,
        slot_id,
        "The save worker could not be started.",
        "Thread.start returned error=%d" % error,
    )
    return false


func _save_worker(slot_id: String, envelope: Dictionary) -> void:
    var result := _write_envelope(slot_id, envelope)
    Callable(self, "_finish_operation").call_deferred("save", slot_id, result)


func _load_worker(slot_id: String) -> void:
    var result := _read_envelope(slot_id)
    Callable(self, "_finish_operation").call_deferred("load", slot_id, result)


func _list_worker() -> void:
    var slots: Dictionary = {}
    for slot_id_value in SLOT_IDS:
        var slot_id := str(slot_id_value)
        var result := _read_envelope(slot_id)
        if bool(result.get("ok", false)):
            slots[slot_id] = {
                "exists": bool(result.get("exists", false)),
                "metadata": (result.get("metadata", {}) as Dictionary).duplicate(true),
                "recovered_backup": bool(result.get("recovered_backup", false)),
            }
        else:
            slots[slot_id] = {
                "exists": true,
                "error": str(result.get("user_message", "Unreadable save")),
                "debug_detail": str(result.get("debug_detail", "")),
            }
    Callable(self, "_finish_operation").call_deferred(
        "list",
        "",
        {"ok": true, "slots": slots},
    )


func _finish_operation(
    operation: String,
    slot_id: String,
    result: Dictionary,
) -> void:
    if _thread != null and _thread.is_alive():
        var tree := Engine.get_main_loop() as SceneTree
        tree.process_frame.connect(
            Callable(self, "_finish_operation").bind(operation, slot_id, result),
            Object.CONNECT_ONE_SHOT,
        )
        return
    if _thread != null and _thread.is_started():
        _thread.wait_to_finish()
    _thread = null
    _busy = false
    busy_changed.emit(false)

    if not bool(result.get("ok", false)):
        operation_failed.emit(
            operation,
            slot_id,
            str(result.get("user_message", "Save operation failed.")),
            str(result.get("debug_detail", "")),
        )
        return

    match operation:
        "save":
            var metadata_value: Variant = result.get("metadata", {})
            var metadata := (
                (metadata_value as Dictionary).duplicate(true)
                if typeof(metadata_value) == TYPE_DICTIONARY
                else {}
            )
            save_completed.emit(slot_id, metadata)
        "load":
            var snapshot_value: Variant = result.get("world_snapshot_json", "")
            var metadata_value: Variant = result.get("metadata", {})
            if typeof(snapshot_value) != TYPE_STRING or str(snapshot_value).strip_edges().is_empty():
                operation_failed.emit(
                    operation,
                    slot_id,
                    "The save did not contain a world snapshot.",
                    "validated load result lost world_snapshot_json string",
                )
                return
            var metadata := (
                (metadata_value as Dictionary).duplicate(true)
                if typeof(metadata_value) == TYPE_DICTIONARY
                else {}
            )
            load_completed.emit(slot_id, str(snapshot_value), metadata)
        "list":
            var slots_value: Variant = result.get("slots", {})
            if typeof(slots_value) == TYPE_DICTIONARY:
                slots_listed.emit((slots_value as Dictionary).duplicate(true))


func _write_envelope(slot_id: String, envelope: Dictionary) -> Dictionary:
    var directory_error := DirAccess.make_dir_recursive_absolute(_root_absolute)
    if directory_error != OK:
        return _failure(
            "The save directory could not be created.",
            "DirAccess.make_dir_recursive_absolute error=%d path=%s"
            % [directory_error, _root_absolute],
        )

    var text := JSON.stringify(envelope, "  ", true, true)
    var bytes := text.to_utf8_buffer()
    if bytes.size() > MAX_SAVE_BYTES:
        return _failure(
            "The world save is too large to write safely.",
            "encoded save size=%d limit=%d" % [bytes.size(), MAX_SAVE_BYTES],
        )

    var final_path := _slot_path(slot_id)
    var temporary_path := final_path + ".tmp"
    var backup_path := final_path + ".bak"
    var file := FileAccess.open(temporary_path, FileAccess.WRITE)
    if file == null:
        return _failure(
            "The save file could not be opened for writing.",
            "FileAccess.open error=%d path=%s" % [FileAccess.get_open_error(), temporary_path],
        )
    var stored := file.store_buffer(bytes)
    file.flush()
    var write_error := file.get_error()
    file.close()
    if not stored or write_error != OK:
        DirAccess.remove_absolute(temporary_path)
        return _failure(
            "The save file could not be written completely.",
            "store_buffer=%s file_error=%d" % [stored, write_error],
        )

    if FileAccess.file_exists(backup_path):
        var old_backup_error := DirAccess.remove_absolute(backup_path)
        if old_backup_error != OK:
            DirAccess.remove_absolute(temporary_path)
            return _failure(
                "The previous save backup could not be replaced.",
                "remove backup error=%d path=%s" % [old_backup_error, backup_path],
            )

    var had_existing := FileAccess.file_exists(final_path)
    if had_existing:
        var backup_error := DirAccess.rename_absolute(final_path, backup_path)
        if backup_error != OK:
            DirAccess.remove_absolute(temporary_path)
            return _failure(
                "The existing save could not be prepared for replacement.",
                "backup rename error=%d path=%s" % [backup_error, final_path],
            )

    var replace_error := DirAccess.rename_absolute(temporary_path, final_path)
    if replace_error != OK:
        if had_existing and FileAccess.file_exists(backup_path):
            DirAccess.rename_absolute(backup_path, final_path)
        DirAccess.remove_absolute(temporary_path)
        return _failure(
            "The new save could not replace the previous file.",
            "final rename error=%d path=%s" % [replace_error, final_path],
        )

    if FileAccess.file_exists(backup_path):
        DirAccess.remove_absolute(backup_path)
    return {
        "ok": true,
        "metadata": (envelope.get("metadata", {}) as Dictionary).duplicate(true),
    }


func _read_envelope(slot_id: String) -> Dictionary:
    var final_path := _slot_path(slot_id)
    var backup_path := final_path + ".bak"
    var path := final_path
    var recovered_backup := false
    if not FileAccess.file_exists(path):
        if FileAccess.file_exists(backup_path):
            path = backup_path
            recovered_backup = true
        else:
            return {"ok": true, "exists": false, "metadata": {}}

    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        return _failure(
            "The save file could not be opened.",
            "FileAccess.open error=%d path=%s" % [FileAccess.get_open_error(), path],
        )
    var length := file.get_length()
    if length <= 0 or length > MAX_SAVE_BYTES:
        file.close()
        return _failure(
            "The save file has an invalid size.",
            "save size=%d limit=%d path=%s" % [length, MAX_SAVE_BYTES, path],
        )
    var bytes := file.get_buffer(length)
    var read_error := file.get_error()
    file.close()
    if bytes.size() != length or (read_error != OK and read_error != ERR_FILE_EOF):
        return _failure(
            "The save file could not be read completely.",
            "read bytes=%d expected=%d file_error=%d" % [bytes.size(), length, read_error],
        )

    var parser := JSON.new()
    var parse_error := parser.parse(bytes.get_string_from_utf8())
    if parse_error != OK:
        return _failure(
            "The save file is not valid JSON.",
            "JSON parse error line=%d message=%s"
            % [parser.get_error_line(), parser.get_error_message()],
        )
    var envelope_value: Variant = parser.data
    if typeof(envelope_value) != TYPE_DICTIONARY:
        return _failure(
            "The save file has an invalid top-level format.",
            "expected dictionary envelope",
        )
    var envelope: Dictionary = envelope_value
    if str(envelope.get("format", "")) != FORMAT_ID:
        return _failure(
            "The save file belongs to an unsupported format.",
            "format=%s expected=%s" % [envelope.get("format", null), FORMAT_ID],
        )
    var version_value: Variant = envelope.get("format_version", null)
    if not _is_integral_number(version_value) or int(version_value) != FORMAT_VERSION:
        return _failure(
            "The save file uses an unsupported version.",
            "format_version=%s expected=%d" % [version_value, FORMAT_VERSION],
        )
    if str(envelope.get("slot_id", "")) != slot_id:
        return _failure(
            "The save file does not match the selected slot.",
            "slot_id=%s expected=%s" % [envelope.get("slot_id", null), slot_id],
        )
    var metadata_value: Variant = envelope.get("metadata", {})
    if typeof(metadata_value) != TYPE_DICTIONARY:
        return _failure(
            "The save metadata is malformed.",
            "metadata must be a dictionary",
        )
    var snapshot_value: Variant = envelope.get("world_snapshot_json", null)
    if typeof(snapshot_value) != TYPE_STRING or str(snapshot_value).strip_edges().is_empty():
        return _failure(
            "The save file does not contain a world snapshot.",
            "world_snapshot_json must be a non-empty string",
        )
    return {
        "ok": true,
        "exists": true,
        "metadata": (metadata_value as Dictionary).duplicate(true),
        "world_snapshot_json": str(snapshot_value),
        "recovered_backup": recovered_backup,
    }


func _slot_path(slot_id: String) -> String:
    return _root_absolute.path_join("%s.json" % slot_id)


static func _is_integral_number(value: Variant) -> bool:
    if typeof(value) == TYPE_INT:
        return true
    return typeof(value) == TYPE_FLOAT and float(value) == float(int(value))


static func _failure(user_message: String, debug_detail: String) -> Dictionary:
    return {
        "ok": false,
        "user_message": user_message,
        "debug_detail": debug_detail,
    }
