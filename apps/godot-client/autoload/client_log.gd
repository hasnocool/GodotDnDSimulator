extends Node

signal entry_added(entry: Dictionary)

const MAX_ENTRIES := 500
const CATEGORIES := PackedStringArray([
    "bridge",
    "state",
    "input",
    "tactical",
    "ui",
    "presentation",
    "performance",
])
const LEVELS := PackedStringArray(["debug", "info", "warning", "error"])

var _entries: Array[Dictionary] = []


func write(
    category: String,
    message: String,
    detail: String = "",
    level: String = "info",
) -> bool:
    if not CATEGORIES.has(category) or not LEVELS.has(level) or message.is_empty():
        return false
    var entry := {
        "category": category,
        "level": level,
        "message": message,
        "detail": detail,
        "timestamp_msec": Time.get_ticks_msec(),
    }
    _entries.append(entry)
    while _entries.size() > MAX_ENTRIES:
        _entries.pop_front()
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


func _detail_suffix(detail: String) -> String:
    if detail.is_empty():
        return ""
    return " — %s" % detail
