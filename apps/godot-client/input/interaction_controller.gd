class_name ClientInteractionController
extends Node

const ClientInputActions = preload("res://input/input_actions.gd")
const InteractionModes = preload("res://input/interaction_modes.gd")

signal mode_changed(mode: int, mode_name: String)
signal select_requested()
signal confirm_requested(mode: int)
signal context_requested(mode: int)
signal cancel_requested(mode: int)
signal modal_cancel_requested()
signal camera_action_requested(action: StringName)
signal command_intent_submitted(request_id: String, correlation_id: String)
signal command_intent_rejected(
    correlation_id: String,
    user_message: String,
    debug_detail: String,
)
signal duplicate_confirmation_ignored(correlation_id: String)
signal pending_command_cancel_ignored(correlation_id: String)

var _state: ClientStateCoordinator
var _input_enabled := false
var _command_intent: Dictionary = {}
var _intent_correlation_id := ""
var _submitted_request_id := ""
var _mode_request_ids: Array[String] = []
var _mode_before_modal := InteractionModes.Mode.INSPECT


func bind_state(state: ClientStateCoordinator) -> void:
    if _state == state:
        return
    unbind_state()
    _state = state
    if _state == null:
        return
    _state.interaction.mode_changed.connect(_on_mode_changed)
    _state.pending_changed.connect(_on_pending_changed)
    _state.command_completed.connect(_on_command_completed)


func unbind_state() -> void:
    if _state != null:
        _disconnect_if_connected(_state.interaction.mode_changed, _on_mode_changed)
        _disconnect_if_connected(_state.pending_changed, _on_pending_changed)
        _disconnect_if_connected(_state.command_completed, _on_command_completed)
    _state = null
    _command_intent.clear()
    _intent_correlation_id = ""
    _submitted_request_id = ""
    _mode_request_ids.clear()


func set_input_enabled(enabled: bool) -> void:
    _input_enabled = enabled
    set_process_unhandled_input(enabled)


func input_enabled() -> bool:
    return _input_enabled


func current_mode() -> int:
    if _state == null:
        return InteractionModes.Mode.INSPECT
    return _state.interaction.mode()


func transition_to(next_mode: int) -> bool:
    if _state == null or not InteractionModes.is_valid(next_mode):
        return false
    if next_mode == InteractionModes.Mode.UI_MODAL:
        return set_ui_modal_active(true)
    var current := _state.interaction.mode()
    if current == next_mode:
        return true
    if _submission_is_pending():
        return false
    if InteractionModes.is_cancellable(current):
        _cancel_mode_requests()
        clear_command_intent()
    return _state.interaction.set_mode(next_mode)


func set_ui_modal_active(active: bool) -> bool:
    if _state == null:
        return false
    var current := _state.interaction.mode()
    if active:
        if current == InteractionModes.Mode.UI_MODAL:
            return true
        if _submission_is_pending():
            return false
        _mode_before_modal = current
        if InteractionModes.is_cancellable(current):
            _cancel_mode_requests()
        return _state.interaction.set_mode(InteractionModes.Mode.UI_MODAL)
    if current != InteractionModes.Mode.UI_MODAL:
        return true
    var restore_mode := _mode_before_modal
    if not InteractionModes.is_valid(restore_mode) or restore_mode == InteractionModes.Mode.UI_MODAL:
        restore_mode = _fallback_mode()
    return _state.interaction.set_mode(restore_mode)


func set_command_intent(command: Dictionary, correlation_id: String) -> bool:
    if _state == null or correlation_id.is_empty():
        return false
    if current_mode() == InteractionModes.Mode.UI_MODAL or _submission_is_pending():
        return false
    if not command.has("command_id") or typeof(command["command_id"]) != TYPE_STRING:
        return false
    if str(command["command_id"]).is_empty():
        return false
    _command_intent = command.duplicate(true)
    _intent_correlation_id = correlation_id
    _submitted_request_id = ""
    return true


func clear_command_intent() -> void:
    if _submission_is_pending():
        return
    _command_intent.clear()
    _intent_correlation_id = ""
    _submitted_request_id = ""


func register_mode_request(request_id: String) -> bool:
    if _state == null or request_id.is_empty():
        return false
    var pending := _state.interaction.pending_requests()
    if not pending.has(request_id):
        return false
    var metadata: Dictionary = pending[request_id]
    if str(metadata.get("request_kind", "")) == "command":
        return false
    if not _mode_request_ids.has(request_id):
        _mode_request_ids.append(request_id)
    return true


func cancel_active_mode() -> bool:
    if _state == null:
        return false
    var mode := _state.interaction.mode()
    if mode == InteractionModes.Mode.UI_MODAL:
        modal_cancel_requested.emit()
        return true
    if _submission_is_pending():
        pending_command_cancel_ignored.emit(_intent_correlation_id)
        return true
    if not InteractionModes.is_cancellable(mode):
        cancel_requested.emit(mode)
        return true
    _cancel_mode_requests()
    _command_intent.clear()
    _intent_correlation_id = ""
    _submitted_request_id = ""
    _state.interaction.set_targeted_actor("")
    return _state.interaction.set_mode(_fallback_mode())


func confirm_current_intent() -> String:
    if _state == null or current_mode() == InteractionModes.Mode.UI_MODAL:
        return ""
    if _submission_is_pending():
        duplicate_confirmation_ignored.emit(_intent_correlation_id)
        return ""
    if _command_intent.is_empty():
        confirm_requested.emit(current_mode())
        return ""
    var request_id := _state.submit_command(_command_intent, _intent_correlation_id)
    if request_id.is_empty():
        return ""
    _submitted_request_id = request_id
    _cancel_mode_requests()
    command_intent_submitted.emit(request_id, _intent_correlation_id)
    return request_id


func handle_semantic_action(action: StringName) -> bool:
    if not _input_enabled or _state == null or not ClientInputActions.is_known(action):
        return false
    if current_mode() == InteractionModes.Mode.UI_MODAL:
        if action == ClientInputActions.CANCEL:
            modal_cancel_requested.emit()
            return true
        return false
    if action == ClientInputActions.CANCEL:
        return cancel_active_mode()
    if action == ClientInputActions.SELECT:
        select_requested.emit()
        return true
    if action == ClientInputActions.CONFIRM:
        confirm_current_intent()
        return true
    if action == ClientInputActions.CONTEXT:
        context_requested.emit(current_mode())
        return true
    if ClientInputActions.is_camera_action(action):
        camera_action_requested.emit(action)
        return true
    return false


func _unhandled_input(event: InputEvent) -> void:
    if not _input_enabled or _state == null:
        return
    if event is InputEventKey and (event as InputEventKey).echo:
        return
    if _ui_has_focus():
        return
    var action := _semantic_action_for_event(event)
    if action.is_empty():
        return
    if handle_semantic_action(action):
        get_viewport().set_input_as_handled()


func _semantic_action_for_event(event: InputEvent) -> StringName:
    if event.is_action_pressed(ClientInputActions.CANCEL):
        return ClientInputActions.CANCEL
    if event.is_action_pressed(ClientInputActions.CONTEXT):
        return ClientInputActions.CONTEXT
    if InteractionModes.is_cancellable(current_mode()):
        if event.is_action_pressed(ClientInputActions.CONFIRM):
            return ClientInputActions.CONFIRM
    if event.is_action_pressed(ClientInputActions.SELECT):
        return ClientInputActions.SELECT
    if event.is_action_pressed(ClientInputActions.CONFIRM):
        return ClientInputActions.CONFIRM
    for camera_action in ClientInputActions.camera_actions():
        if event.is_action_pressed(camera_action):
            return camera_action
    return &""


func _ui_has_focus() -> bool:
    if not is_inside_tree():
        return false
    return get_viewport().gui_get_focus_owner() != null


func _fallback_mode() -> int:
    if _state != null and not _state.interaction.selected_actor_id().is_empty():
        return InteractionModes.Mode.SELECT
    return InteractionModes.Mode.INSPECT


func _cancel_mode_requests() -> void:
    if _state == null:
        _mode_request_ids.clear()
        return
    var request_ids := _mode_request_ids.duplicate()
    _mode_request_ids.clear()
    for request_id in request_ids:
        _state.cancel_pending(request_id)


func _submission_is_pending() -> bool:
    if _state == null or _submitted_request_id.is_empty():
        return false
    if _state.interaction.pending_requests().has(_submitted_request_id):
        return true
    _submitted_request_id = ""
    return false


func _on_mode_changed(mode: int, _generation: int) -> void:
    mode_changed.emit(mode, InteractionModes.name_of(mode))


func _on_pending_changed(_pending_count: int) -> void:
    if _state == null:
        return
    var pending := _state.interaction.pending_requests()
    for index in range(_mode_request_ids.size() - 1, -1, -1):
        if not pending.has(_mode_request_ids[index]):
            _mode_request_ids.remove_at(index)
    if not _submitted_request_id.is_empty() and not pending.has(_submitted_request_id):
        _submitted_request_id = ""


func _on_command_completed(
    correlation_id: String,
    accepted: bool,
    user_message: String,
    debug_detail: String,
) -> void:
    if correlation_id != _intent_correlation_id:
        return
    _submitted_request_id = ""
    if not accepted:
        command_intent_rejected.emit(correlation_id, user_message, debug_detail)
        return
    _command_intent.clear()
    _intent_correlation_id = ""
    if _state != null and InteractionModes.is_cancellable(_state.interaction.mode()):
        _mode_request_ids.clear()
        _state.interaction.set_targeted_actor("")
        _state.interaction.set_mode(_fallback_mode())


func _disconnect_if_connected(signal_value: Signal, callable: Callable) -> void:
    if signal_value.is_connected(callable):
        signal_value.disconnect(callable)
