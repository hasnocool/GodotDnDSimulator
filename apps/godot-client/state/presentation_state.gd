class_name PresentationState
extends RefCounted

signal scene_changed(active_scene_id: String, loading_scene_id: String)
signal activity_changed(active_presentations: int)
signal options_changed()

var _active_scene_id := ""
var _loading_scene_id := ""
var _active_presentations := 0
var _reduced_motion := false
var _ui_scale := 1.0
var _debug_visible := false


func active_scene_id() -> String:
    return _active_scene_id


func loading_scene_id() -> String:
    return _loading_scene_id


func active_presentations() -> int:
    return _active_presentations


func reduced_motion() -> bool:
    return _reduced_motion


func ui_scale() -> float:
    return _ui_scale


func debug_visible() -> bool:
    return _debug_visible


func set_loading_scene(scene_id: String) -> void:
    if scene_id == _loading_scene_id:
        return
    _loading_scene_id = scene_id
    scene_changed.emit(_active_scene_id, _loading_scene_id)


func set_active_scene(scene_id: String) -> void:
    if scene_id == _active_scene_id and _loading_scene_id.is_empty():
        return
    _active_scene_id = scene_id
    _loading_scene_id = ""
    scene_changed.emit(_active_scene_id, _loading_scene_id)


func begin_presentation() -> void:
    _active_presentations += 1
    activity_changed.emit(_active_presentations)


func finish_presentation() -> void:
    if _active_presentations == 0:
        return
    _active_presentations -= 1
    activity_changed.emit(_active_presentations)


func clear_presentations() -> void:
    if _active_presentations == 0:
        return
    _active_presentations = 0
    activity_changed.emit(0)


func apply_local_options(
    reduced_motion_value: bool,
    ui_scale_value: float,
    debug_visible_value: bool,
) -> void:
    _reduced_motion = reduced_motion_value
    _ui_scale = clampf(ui_scale_value, 0.75, 2.0)
    _debug_visible = debug_visible_value
    options_changed.emit()
