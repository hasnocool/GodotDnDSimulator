extends Node

signal entry_added(entry: Dictionary)

const MAX_ENTRIES := 1000
const MAX_PENDING_LINES := 4096
const LOG_DIRECTORY := "user://logs"

static func _categories() -> PackedStringArray:
    return PackedStringArray([
        "bridge",
        "state",
        "input",
        "tactical",
        "ui",
        "presentation",
        "performance",
        "automation",
        "agent",
    ])

static func _levels() -> PackedStringArray:
    return PackedStringArray(["debug", "info", "warning", "error"])

var _entries: Array[Dictionary] = []
var _writer_thread := Thread.new()
var _writer_mutex := Mutex.new()
var _writer_semaphore := Semaphore.new()
var _pending_lines: Array[String] = []
var _writer_stop := false
var _writer_started := false
var _dropped_lines := 0
var _disk_path := ""
var _disk_path_absolute := ""
var _log_directory_absolute := ""


func _ready() -> void:
    _start_disk_writer()


func _exit_tree() -> void:
    _stop_disk_writer()


func write(
    category: String,
    message: String,
    detail: String = "",
    level: String = "info",
    fields: Dictionary = {},
) -> bool:
    if not _categories().has(category) or not _levels().has(level) or message.is_empty():
        return false
    var entry := {
        "category": category,
        "level": level,
        "message": message,
        "detail": detail,
        "timestamp_msec": Time.get_ticks_msec(),
        "unix_time_msec": int(Time.get_unix_time_from_system() * 1000.0),
        "frame": Engine.get_process_frames(),
        "fields": fields.duplicate(true),
    }
    _entries.append(entry)
    while _entries.size() > MAX_ENTRIES:
        _entries.pop_front()
    _queue_disk_entry(entry)
    entry_added.emit(entry.duplicate(true))
    if level == "error":
        push_error("[%s] %s%s" % [category, message, _detail_suffix(detail)])
    elif level == "warning":
        push_warning("[%s] %s%s" % [category, message, _detail_suffix(detail)])
    return true


func entries(category: String = "") -> Array:
    var result: Array = []
    for entry in _entries:
        if not category.is_empty() and str(entry.get("category", "")) != category:
            continue
        result.append(entry.duplicate(true))
    return result


func clear() -> void:
    _entries.clear()


func disk_log_path() -> String:
    return _disk_path


func disk_logging_active() -> bool:
    return _writer_started and not _writer_stop


func _start_disk_writer() -> void:
    if _writer_started:
        return
    var stamp := Time.get_datetime_string_from_system(true, false).replace(":", "-")
    _disk_path = "%s/client-%s.jsonl" % [LOG_DIRECTORY, stamp]
    _disk_path_absolute = ProjectSettings.globalize_path(_disk_path)
    _log_directory_absolute = ProjectSettings.globalize_path(LOG_DIRECTORY)
    _writer_stop = false
    var error := _writer_thread.start(_writer_loop)
    if error != OK:
        _disk_path = ""
        _disk_path_absolute = ""
        _log_directory_absolute = ""
        push_warning("Unable to start client disk-log writer: %s" % error_string(error))
        return
    _writer_started = true


func _stop_disk_writer() -> void:
    if not _writer_started:
        return
    _writer_mutex.lock()
    _writer_stop = true
    _writer_mutex.unlock()
    _writer_semaphore.post()
    _writer_thread.wait_to_finish()
    _writer_started = false


func _queue_disk_entry(entry: Dictionary) -> void:
    if not _writer_started:
        return
    var line := JSON.stringify(entry)
    _writer_mutex.lock()
    if _writer_stop:
        _writer_mutex.unlock()
        return
    if _pending_lines.size() >= MAX_PENDING_LINES:
        _pending_lines.pop_front()
        _dropped_lines += 1
    _pending_lines.append(line)
    _writer_mutex.unlock()
    _writer_semaphore.post()


func _writer_loop() -> void:
    var mkdir_error := DirAccess.make_dir_recursive_absolute(_log_directory_absolute)
    if mkdir_error != OK and mkdir_error != ERR_ALREADY_EXISTS:
        return
    var file := FileAccess.open(_disk_path_absolute, FileAccess.WRITE)
    if file == null:
        return
    while true:
        _writer_semaphore.wait()
        var lines: Array[String] = []
        var dropped := 0
        var should_stop := false
        _writer_mutex.lock()
        lines.assign(_pending_lines)
        _pending_lines.clear()
        dropped = _dropped_lines
        _dropped_lines = 0
        should_stop = _writer_stop
        _writer_mutex.unlock()
        if dropped > 0:
            file.store_line(
                JSON.stringify({
                    "category": "automation",
                    "level": "warning",
                    "message": "client disk-log queue dropped entries",
                    "dropped": dropped,
                    "unix_time_msec": int(Time.get_unix_time_from_system() * 1000.0),
                })
            )
        for line in lines:
            file.store_line(line)
        file.flush()
        if should_stop:
            break
    file.close()


func _detail_suffix(detail: String) -> String:
    if detail.is_empty():
        return ""
    return " — %s" % detail
