class_name AuthoritativeMirror
extends RefCounted

signal snapshot_replaced(snapshot: Dictionary, sequence: int)
signal events_appended(events: Array, sequence: int)
signal cleared()

var _snapshot: Dictionary = {}
var _event_history: Array[Dictionary] = []
var _sequence := 0
var _has_snapshot := false


func reset() -> void:
    _snapshot.clear()
    _event_history.clear()
    _sequence = 0
    _has_snapshot = false
    cleared.emit()


func has_snapshot() -> bool:
    return _has_snapshot


func sequence() -> int:
    return _sequence


func snapshot() -> Dictionary:
    return _snapshot.duplicate(true)


func state_view() -> Dictionary:
    if not _has_snapshot:
        return {}
    var raw_state: Variant = _snapshot.get("state", {})
    if typeof(raw_state) != TYPE_DICTIONARY:
        return {}
    var state: Dictionary = raw_state
    return state.duplicate(true)


func recent_events() -> Array:
    var result: Array = []
    for event in _event_history:
        result.append(event.duplicate(true))
    return result


func reconstruction_view() -> Dictionary:
    return {
        "snapshot": snapshot(),
        "events": recent_events(),
        "sequence": _sequence,
    }


func ingest_snapshot(snapshot_value: Dictionary) -> bool:
    var state_value: Variant = snapshot_value.get("state", {})
    if typeof(state_value) != TYPE_DICTIONARY:
        return false
    var state: Dictionary = state_value
    var sequence_value: Variant = state.get("sequence")
    if typeof(sequence_value) != TYPE_INT or int(sequence_value) < 0:
        return false
    var next_sequence := int(sequence_value)
    if _has_snapshot and next_sequence < _sequence:
        return false

    _snapshot = snapshot_value.duplicate(true)
    _sequence = next_sequence
    _has_snapshot = true
    _event_history.clear()
    snapshot_replaced.emit(snapshot(), _sequence)
    return true


func ingest_events(events_value: Array) -> bool:
    var accepted: Array[Dictionary] = []
    var expected := _sequence + 1

    for raw_event in events_value:
        if typeof(raw_event) != TYPE_DICTIONARY:
            return false
        var event: Dictionary = raw_event
        var sequence_value: Variant = event.get("sequence")
        if typeof(sequence_value) != TYPE_INT or int(sequence_value) < 1:
            return false
        var event_sequence := int(sequence_value)
        if event_sequence <= _sequence:
            continue
        if event_sequence != expected:
            return false
        accepted.append(event.duplicate(true))
        expected += 1

    if accepted.is_empty():
        return true

    for event in accepted:
        _event_history.append(event)

    _sequence = expected - 1
    var emitted_events: Array = []
    for event in accepted:
        emitted_events.append(event.duplicate(true))
    events_appended.emit(emitted_events, _sequence)
    return true
