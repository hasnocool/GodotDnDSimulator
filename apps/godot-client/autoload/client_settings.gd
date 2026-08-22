extends Node

signal setting_changed(key: String, value: Variant)

const SETTINGS_PATH := "user://client_settings.cfg"
const SECTION := "presentation"

var _values := {
    "ui_scale": 1.0,
    "reduced_motion": false,
    "debug_overlay": false,
    "master_volume_db": 0.0,
}


func _ready() -> void:
    load_settings()


func value(key: String, fallback: Variant = null) -> Variant:
    return _values.get(key, fallback)


func ui_scale() -> float:
    return float(_values["ui_scale"])


func reduced_motion() -> bool:
    return bool(_values["reduced_motion"])


func debug_overlay() -> bool:
    return bool(_values["debug_overlay"])


func master_volume_db() -> float:
    return float(_values["master_volume_db"])


func set_value(key: String, new_value: Variant, persist: bool = true) -> bool:
    if not _values.has(key):
        return false
    var normalized: Variant = _normalize(key, new_value)
    if normalized == null:
        return false
    if _values[key] == normalized:
        return true
    _values[key] = normalized
    setting_changed.emit(key, normalized)
    if persist:
        save_settings()
    return true


func load_settings() -> void:
    var config := ConfigFile.new()
    var result := config.load(SETTINGS_PATH)
    if result != OK and result != ERR_FILE_NOT_FOUND:
        push_warning("Unable to load client settings: %s" % error_string(result))
        return
    if result == ERR_FILE_NOT_FOUND:
        return
    for key in _values.keys():
        if not config.has_section_key(SECTION, str(key)):
            continue
        var normalized: Variant = _normalize(str(key), config.get_value(SECTION, str(key)))
        if normalized != null:
            _values[key] = normalized


func save_settings() -> bool:
    var config := ConfigFile.new()
    for key in _values.keys():
        config.set_value(SECTION, str(key), _values[key])
    var result := config.save(SETTINGS_PATH)
    if result != OK:
        push_warning("Unable to save client settings: %s" % error_string(result))
        return false
    return true


func reset_defaults(persist: bool = true) -> void:
    var defaults := {
        "ui_scale": 1.0,
        "reduced_motion": false,
        "debug_overlay": false,
        "master_volume_db": 0.0,
    }
    for key in defaults:
        if _values[key] == defaults[key]:
            continue
        _values[key] = defaults[key]
        setting_changed.emit(str(key), defaults[key])
    if persist:
        save_settings()


func _normalize(key: String, candidate: Variant) -> Variant:
    match key:
        "ui_scale":
            var value_type := typeof(candidate)
            if value_type != TYPE_FLOAT and value_type != TYPE_INT:
                return null
            return clampf(float(candidate), 0.75, 2.0)
        "reduced_motion", "debug_overlay":
            if typeof(candidate) != TYPE_BOOL:
                return null
            return candidate
        "master_volume_db":
            var value_type := typeof(candidate)
            if value_type != TYPE_FLOAT and value_type != TYPE_INT:
                return null
            return clampf(float(candidate), -80.0, 6.0)
        _:
            return null
