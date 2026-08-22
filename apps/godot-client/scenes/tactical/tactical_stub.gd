class_name TacticalPresentationStub
extends Node3D

var _client_state: ClientStateCoordinator
var _bound_sequence := 0


func bind_client_state(state: ClientStateCoordinator) -> void:
    if _client_state != null and _client_state.authoritative_changed.is_connected(_on_authoritative_changed):
        _client_state.authoritative_changed.disconnect(_on_authoritative_changed)
    _client_state = state
    _bound_sequence = 0 if _client_state == null else _client_state.authoritative.sequence()
    if _client_state != null:
        _client_state.authoritative_changed.connect(_on_authoritative_changed)


func bound_sequence() -> int:
    return _bound_sequence


func authoritative_snapshot() -> Dictionary:
    if _client_state == null:
        return {}
    return _client_state.authoritative.snapshot()


func authoritative_reconstruction_view() -> Dictionary:
    if _client_state == null:
        return {}
    return _client_state.authoritative.reconstruction_view()


func _exit_tree() -> void:
    if _client_state != null and _client_state.authoritative_changed.is_connected(_on_authoritative_changed):
        _client_state.authoritative_changed.disconnect(_on_authoritative_changed)


func _on_authoritative_changed(sequence: int) -> void:
    _bound_sequence = sequence
