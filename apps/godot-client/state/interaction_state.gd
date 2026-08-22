class_name InteractionState
extends RefCounted

signal selection_changed(actor_id: String, generation: int)
signal hover_changed(actor_id: String, generation: int)
signal target_changed(actor_id: String, generation: int)
signal pending_changed(pending_count: int)
signal generation_changed(generation: int)

var _selected_actor_id := ""
var _hovered_actor_id := ""
var _targeted_actor_id := ""
var _generation := 0
var _pending: Dictionary = {}


func selected_actor_id() -> String:
    return _selected_actor_id


func hovered_actor_id() -> String:
    return _hovered_actor_id


func targeted_actor_id() -> String:
    return _targeted_actor_id


func generation() -> int:
    return _generation


func pending_count() -> int:
    return _pending.size()


func pending_requests() -> Dictionary:
    return _pending.duplicate(true)


func set_selected_actor(actor_id: String) -> void:
    if actor_id == _selected_actor_id:
        return
    _selected_actor_id = actor_id
    _advance_generation()
    selection_changed.emit(_selected_actor_id, _generation)


func set_hovered_actor(actor_id: String) -> void:
    if actor_id == _hovered_actor_id:
        return
    _hovered_actor_id = actor_id
    _advance_generation()
    hover_changed.emit(_hovered_actor_id, _generation)


func set_targeted_actor(actor_id: String) -> void:
    if actor_id == _targeted_actor_id:
        return
    _targeted_actor_id = actor_id
    _advance_generation()
    target_changed.emit(_targeted_actor_id, _generation)


func clear_actor_focus() -> void:
    var changed := false
    if not _selected_actor_id.is_empty():
        _selected_actor_id = ""
        changed = true
    if not _hovered_actor_id.is_empty():
        _hovered_actor_id = ""
        changed = true
    if not _targeted_actor_id.is_empty():
        _targeted_actor_id = ""
        changed = true
    if changed:
        _advance_generation()
        selection_changed.emit("", _generation)
        hover_changed.emit("", _generation)
        target_changed.emit("", _generation)


func track_pending(
    request_id: String,
    request_kind: String,
    correlation_id: String,
    generation_value: int,
) -> bool:
    if request_id.is_empty() or request_kind.is_empty() or correlation_id.is_empty():
        return false
    if generation_value < 0 or _pending.has(request_id):
        return false
    _pending[request_id] = {
        "request_kind": request_kind,
        "correlation_id": correlation_id,
        "generation": generation_value,
    }
    pending_changed.emit(_pending.size())
    return true


func clear_pending(request_id: String) -> bool:
    if not _pending.has(request_id):
        return false
    _pending.erase(request_id)
    pending_changed.emit(_pending.size())
    return true


func clear_pending_matching(correlation_id: String, request_kind: String = "") -> int:
    var removed := 0
    var ids: Array = _pending.keys()
    for request_id_value in ids:
        var request_id := str(request_id_value)
        var metadata: Dictionary = _pending[request_id]
        if str(metadata.get("correlation_id", "")) != correlation_id:
            continue
        if not request_kind.is_empty() and str(metadata.get("request_kind", "")) != request_kind:
            continue
        _pending.erase(request_id)
        removed += 1
    if removed > 0:
        pending_changed.emit(_pending.size())
    return removed


func clear_all_pending() -> void:
    if _pending.is_empty():
        return
    _pending.clear()
    pending_changed.emit(0)


func _advance_generation() -> void:
    _generation += 1
    generation_changed.emit(_generation)
