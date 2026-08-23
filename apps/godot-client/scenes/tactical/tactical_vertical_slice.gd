class_name TacticalVerticalSlice
extends Node3D

const ActorScene = preload("res://scenes/actors/tactical_actor_view.tscn")
const InteractionModes = preload("res://input/interaction_modes.gd")
const DEBUG_SHAPE_KINDS := ["sphere", "cylinder", "cone", "line"]

var _state: ClientStateCoordinator
var _controller: ClientInteractionController
var _tactical: Dictionary = {}
var _actor_views: Dictionary = {}
var _last_space: Dictionary = {}
var _command_counter := 0
var _hovered_cell: Dictionary = {}
var _armed_cell: Dictionary = {}
var _armed_target := ""
var _path_request_id := ""
var _reachable_request_id := ""
var _target_request_id := ""
var _area_request_id := ""
var _preview_authority_sequence := -1
var _debug_shape_index := 0
var _debug_shape_direction := Vector2.RIGHT

@onready var _map: TacticalMapView = $TacticalMap
@onready var _actors_root: Node3D = $Actors
@onready var _overlay: TacticalOverlay = $TacticalOverlay
@onready var _camera_rig: TacticalCameraController = $TacticalCamera
@onready var _camera: Camera3D = $TacticalCamera/Yaw/Tilt/Camera3D
@onready var _event_presenter: TacticalEventPresenter = $EventPresenter
@onready var _vfx_presenter: TacticalVFXPresenter = $VFXPresenter
@onready var _occlusion: TacticalOcclusionController = $OcclusionController
@onready var _hud: TacticalHUD = $HUD/TacticalHUD


func _ready() -> void:
    _overlay.bind_map(_map)
    _hud.move_requested.connect(_on_move_requested)
    _hud.strike_requested.connect(_on_strike_requested)
    _hud.end_turn_requested.connect(_on_end_turn_requested)
    _hud.area_debug_requested.connect(_on_area_debug_requested)
    _hud.shape_kind_requested.connect(_on_shape_kind_requested)
    _hud.shape_rotate_requested.connect(_on_shape_rotate_requested)
    _hud.set_shape_debug_state(_debug_shape_kind(), _debug_shape_direction)
    _event_presenter.combat_log_entry.connect(_hud.append_log)
    _event_presenter.actor_emphasis_requested.connect(_on_actor_emphasis_requested)
    _event_presenter.vfx_cue_requested.connect(_on_vfx_cue_requested)


func bind_client_state(state: ClientStateCoordinator) -> void:
    if _state == state:
        _refresh_from_authority()
        return
    _unbind_state()
    _state = state
    if _state == null:
        return
    _state.authoritative_changed.connect(_on_authoritative_changed)
    _state.query_completed.connect(_on_query_completed)
    _state.preview_completed.connect(_on_preview_completed)
    _state.command_completed.connect(_on_command_completed)
    _state.interaction.selection_changed.connect(_on_selection_changed)
    _state.interaction.hover_changed.connect(_on_hover_changed)
    _state.interaction.mode_changed.connect(_on_interaction_mode_changed)
    _state.presentation.options_changed.connect(_on_presentation_options_changed)
    _event_presenter.bind_state(_state)
    _camera_rig.set_reduced_motion(_state.presentation.reduced_motion())
    _refresh_from_authority()


func bind_interaction_controller(controller: ClientInteractionController) -> void:
    if _controller == controller:
        return
    _unbind_controller()
    _controller = controller
    if _controller == null:
        return
    _controller.camera_action_requested.connect(_on_camera_action_requested)
    _controller.select_requested.connect(_on_select_requested)
    _controller.confirm_requested.connect(_on_confirm_requested)
    _controller.context_requested.connect(_on_context_requested)
    _controller.mode_changed.connect(_on_controller_mode_changed)
    _controller.command_intent_rejected.connect(_on_intent_rejected)


func authoritative_sequence() -> int:
    if _state == null:
        return 0
    return _state.authoritative.sequence()


func actor_view(actor_id: String) -> TacticalActorView:
    return _actor_views.get(actor_id) as TacticalActorView


func current_tactical_state() -> Dictionary:
    return _tactical.duplicate(true)


func request_move_mode() -> void:
    _on_move_requested()


func request_strike_mode() -> void:
    _on_strike_requested()


func request_end_turn() -> void:
    _on_end_turn_requested()


func debug_overlay() -> TacticalOverlay:
    return _overlay


func tactical_hud() -> TacticalHUD:
    return _hud


func vfx_presenter() -> TacticalVFXPresenter:
    return _vfx_presenter


func debug_shape_kind() -> String:
    return _debug_shape_kind()


func debug_shape_direction() -> Vector2:
    return _debug_shape_direction


func _exit_tree() -> void:
    _cancel_scene_preview_requests()
    _unbind_controller()
    _unbind_state()
    _occlusion.clear()
    _overlay.clear_debug()


func _unhandled_input(event: InputEvent) -> void:
    if _state == null or _controller == null:
        return
    if event is InputEventMouseMotion:
        _update_pointer_hover((event as InputEventMouseMotion).position)


func _refresh_from_authority() -> void:
    if _state == null or not _state.authoritative.has_snapshot():
        return
    var view := _state.authoritative.state_view()
    if str(view.get("mode", "")) != "tactical_vertical_slice":
        _hud.set_error("Authoritative state is not the v0.7 tactical slice")
        return
    var tactical_value: Variant = view.get("tactical", {})
    if typeof(tactical_value) != TYPE_DICTIONARY:
        _hud.set_error("Authoritative tactical state is malformed")
        return
    _tactical = (tactical_value as Dictionary).duplicate(true)
    var space_value: Variant = _tactical.get("space", {})
    var space: Dictionary = space_value if typeof(space_value) == TYPE_DICTIONARY else {}
    if space != _last_space:
        _last_space = space.duplicate(true)
        _map.apply_authoritative_space(space)
        _camera_rig.set_map_bounds(_map.camera_bounds())
    _reconcile_actor_views()
    _ensure_selection()
    _refresh_indicators()
    _refresh_debug_layers()
    _hud.apply_tactical_state(
        _tactical,
        _state.interaction.selected_actor_id(),
    )
    _request_actions()
    _refresh_occlusion()
    _refresh_active_preview_after_state_change()


func _reconcile_actor_views() -> void:
    var seen: Dictionary = {}
    var actors_value: Variant = _tactical.get("actors", [])
    if typeof(actors_value) != TYPE_ARRAY:
        return
    for actor_value in actors_value:
        if typeof(actor_value) != TYPE_DICTIONARY:
            continue
        var actor: Dictionary = actor_value
        var actor_id := str(actor.get("actor_id", ""))
        if actor_id.is_empty():
            continue
        seen[actor_id] = true
        var position_value: Variant = actor.get("position", {})
        if typeof(position_value) != TYPE_DICTIONARY:
            continue
        var cell: Dictionary = position_value
        if not _map.contains_cell(cell):
            ClientLog.write(
                "tactical",
                "Authoritative actor is outside visual map",
                "%s at %s" % [actor_id, cell],
                "warning",
            )
            continue
        var view := actor_view(actor_id)
        if view == null:
            view = ActorScene.instantiate() as TacticalActorView
            if view == null:
                continue
            _actors_root.add_child(view)
            _actor_views[actor_id] = view
        view.bind_actor(
            actor,
            _map.cell_to_world(cell),
            _state.presentation.reduced_motion(),
        )
        view.set_debug_identity_visible(_state.presentation.debug_visible())
    for actor_id_value in _actor_views.keys():
        var actor_id := str(actor_id_value)
        if seen.has(actor_id):
            continue
        var stale := actor_view(actor_id)
        if stale != null:
            stale.queue_free()
        _actor_views.erase(actor_id)


func _ensure_selection() -> void:
    if _state == null:
        return
    var selected := _state.interaction.selected_actor_id()
    if not selected.is_empty() and _actor_views.has(selected):
        return
    var current := str(_tactical.get("current_actor_id", ""))
    if not current.is_empty() and _actor_views.has(current):
        _state.interaction.set_selected_actor(current)
        if _controller != null:
            _controller.transition_to(InteractionModes.Mode.SELECT)


func _refresh_indicators() -> void:
    if _state == null:
        return
    var selected := _state.interaction.selected_actor_id()
    var hovered := _state.interaction.hovered_actor_id()
    var current := str(_tactical.get("current_actor_id", ""))
    for actor_id_value in _actor_views.keys():
        var actor_id := str(actor_id_value)
        var view := actor_view(actor_id)
        if view == null:
            continue
        view.set_selected(actor_id == selected)
        view.set_hovered(actor_id == hovered)
        view.set_current_turn(actor_id == current)
        view.set_debug_identity_visible(_state.presentation.debug_visible())


func _refresh_debug_layers() -> void:
    if _state == null:
        return
    var visible := _state.presentation.debug_visible()
    _map.set_debug_labels_visible(visible)
    _overlay.show_occupancy(_tactical.get("actors", []), visible)
    for actor_id_value in _actor_views.keys():
        var view := actor_view(str(actor_id_value))
        if view != null:
            view.set_debug_identity_visible(visible)


func _request_actions() -> void:
    if _state == null:
        return
    var selected := _state.interaction.selected_actor_id()
    if selected.is_empty():
        return
    _state.request_query(
        "tactical.actions",
        {"actor_id": selected},
        "v07-actions:%s" % selected,
    )


func _request_reachable_for_selected() -> void:
    if _state == null or _controller == null:
        return
    var actor_id := _state.interaction.selected_actor_id()
    if actor_id.is_empty():
        return
    if not _reachable_request_id.is_empty():
        _state.cancel_pending(_reachable_request_id)
    _reachable_request_id = _state.request_preview(
        "spatial.reachable",
        {
            "entity_id": actor_id,
            "movement_mode": "walk",
        },
        "v07-reachable:%s" % actor_id,
    )
    _controller.register_mode_request(_reachable_request_id)


func _on_move_requested() -> void:
    if _state == null or _controller == null:
        return
    var actor_id := _state.interaction.selected_actor_id()
    if actor_id.is_empty() or not _controller.transition_to(InteractionModes.Mode.MOVE):
        return
    _controller.clear_command_intent()
    _armed_cell.clear()
    _overlay.clear_all()
    _request_reachable_for_selected()
    _hud.set_preview_text("Choose a destination within authoritative movement range")


func _on_strike_requested() -> void:
    if _state == null or _controller == null:
        return
    if _state.interaction.selected_actor_id().is_empty():
        return
    if not _controller.transition_to(InteractionModes.Mode.TARGET):
        return
    _controller.clear_command_intent()
    _armed_target = ""
    _overlay.clear_all()
    _hud.set_preview_text(
        "Choose a target; reach, LOS, and cover come from the engine · Context cycles targets"
    )


func _on_end_turn_requested() -> void:
    if _state == null or _controller == null:
        return
    var actor_id := str(_tactical.get("current_actor_id", ""))
    if actor_id.is_empty():
        return
    _controller.transition_to(InteractionModes.Mode.SELECT)
    if _controller.set_command_intent(
        _command("tactical.end_turn", actor_id, {}),
        "v07-end-turn:%d" % _state.authoritative.sequence(),
    ):
        _controller.confirm_current_intent()


func _on_area_debug_requested() -> void:
    if _state == null or _controller == null:
        return
    var actor_id := _state.interaction.selected_actor_id()
    var actor := _actor_data(actor_id)
    if actor.is_empty():
        return
    var position_value: Variant = actor.get("position", {})
    if typeof(position_value) != TYPE_DICTIONARY:
        return
    if not _controller.transition_to(InteractionModes.Mode.SHAPE_PREVIEW):
        return
    _overlay.clear_all()
    _hud.set_shape_debug_state(_debug_shape_kind(), _debug_shape_direction)
    _request_area_at(position_value)


func _on_shape_kind_requested() -> void:
    _debug_shape_index = (_debug_shape_index + 1) % DEBUG_SHAPE_KINDS.size()
    _hud.set_shape_debug_state(_debug_shape_kind(), _debug_shape_direction)
    if _controller != null and _controller.current_mode() == InteractionModes.Mode.SHAPE_PREVIEW:
        var origin := _shape_origin()
        if not origin.is_empty():
            _request_area_at(origin)


func _on_shape_rotate_requested() -> void:
    _debug_shape_direction = Vector2(-_debug_shape_direction.y, _debug_shape_direction.x)
    _hud.set_shape_debug_state(_debug_shape_kind(), _debug_shape_direction)
    if _controller != null and _controller.current_mode() == InteractionModes.Mode.SHAPE_PREVIEW:
        var origin := _shape_origin()
        if not origin.is_empty():
            _request_area_at(origin)


func _on_select_requested() -> void:
    if _controller == null:
        return
    var hit := _pick(get_viewport().get_mouse_position())
    var mode := _controller.current_mode()
    if mode == InteractionModes.Mode.MOVE:
        var cell := _cell_from_hit(hit)
        if cell.is_empty():
            return
        if cell == _armed_cell:
            _controller.confirm_current_intent()
        else:
            _request_path(cell)
        return
    if mode == InteractionModes.Mode.TARGET:
        var target_id := _actor_from_hit(hit)
        if target_id.is_empty():
            return
        if target_id == _armed_target:
            _controller.confirm_current_intent()
        else:
            _request_attack_preview(target_id)
        return
    if mode == InteractionModes.Mode.SHAPE_PREVIEW:
        var area_cell := _cell_from_hit(hit)
        if not area_cell.is_empty():
            _request_area_at(area_cell)
        return
    var actor_id := _actor_from_hit(hit)
    if _state != null:
        _state.interaction.set_selected_actor(actor_id)
        if not actor_id.is_empty():
            _controller.transition_to(InteractionModes.Mode.SELECT)


func _on_confirm_requested(mode: int) -> void:
    if mode == InteractionModes.Mode.MOVE:
        _hud.set_preview_text("Choose a legal path destination before confirming")
    elif mode == InteractionModes.Mode.TARGET:
        _hud.set_preview_text("Choose an engine-approved target before confirming")


func _on_context_requested(mode: int) -> void:
    if mode == InteractionModes.Mode.TARGET:
        _cycle_target()
        return
    if mode == InteractionModes.Mode.SHAPE_PREVIEW:
        _on_shape_rotate_requested()
        return
    if mode not in [InteractionModes.Mode.INSPECT, InteractionModes.Mode.SELECT]:
        return
    _cycle_selection()


func _on_camera_action_requested(action: StringName) -> void:
    if action == ClientInputActions.CAMERA_FOCUS:
        _focus_selected_or_current()
        return
    _camera_rig.handle_camera_action(action)
    _refresh_occlusion()


func _on_controller_mode_changed(mode: int, _mode_name: String) -> void:
    if mode not in [
        InteractionModes.Mode.MOVE,
        InteractionModes.Mode.TARGET,
        InteractionModes.Mode.SHAPE_PREVIEW,
    ]:
        _overlay.clear_all()
        _armed_cell.clear()
        _armed_target = ""
        if _state != null:
            _state.interaction.set_targeted_actor("")
    _request_actions()


func _on_intent_rejected(
    _correlation_id: String,
    user_message: String,
    debug_detail: String,
) -> void:
    _hud.set_error(user_message, debug_detail)


func _update_pointer_hover(pointer: Vector2) -> void:
    if _controller == null or _state == null:
        return
    var hit := _pick(pointer)
    var mode := _controller.current_mode()
    if mode == InteractionModes.Mode.MOVE:
        var cell := _cell_from_hit(hit)
        if not cell.is_empty() and cell != _hovered_cell:
            _hovered_cell = cell
            _request_path(cell)
        return
    if mode == InteractionModes.Mode.TARGET:
        var actor_id := _actor_from_hit(hit)
        if actor_id != _state.interaction.hovered_actor_id():
            _state.interaction.set_hovered_actor(actor_id)
        if not actor_id.is_empty() and actor_id != _armed_target:
            _request_attack_preview(actor_id)
        return
    var hover_actor := _actor_from_hit(hit)
    _state.interaction.set_hovered_actor(hover_actor)


func _request_path(cell: Dictionary) -> void:
    if _state == null or _controller == null:
        return
    var actor_id := _state.interaction.selected_actor_id()
    if actor_id.is_empty():
        return
    _controller.clear_command_intent()
    _armed_cell.clear()
    _hovered_cell = cell.duplicate(true)
    if not _path_request_id.is_empty():
        _state.cancel_pending(_path_request_id)
    var correlation := "v07-path:%d:%d" % [
        int(cell.get("x", 0)),
        int(cell.get("y", 0)),
    ]
    _path_request_id = _state.request_preview(
        "spatial.path",
        {
            "entity_id": actor_id,
            "destination": cell,
            "movement_mode": "walk",
        },
        correlation,
    )
    _controller.register_mode_request(_path_request_id)


func _request_attack_preview(target_id: String) -> void:
    if _state == null or _controller == null:
        return
    var attacker_id := _state.interaction.selected_actor_id()
    if attacker_id.is_empty() or target_id == attacker_id:
        return
    _controller.clear_command_intent()
    _armed_target = ""
    _state.interaction.set_targeted_actor(target_id)
    if not _target_request_id.is_empty():
        _state.cancel_pending(_target_request_id)
    _target_request_id = _state.request_preview(
        "tactical.attack",
        {"attacker_id": attacker_id, "target_id": target_id},
        "v07-attack:%s" % target_id,
    )
    _controller.register_mode_request(_target_request_id)


func _request_area_at(cell: Dictionary) -> void:
    if _state == null or _controller == null:
        return
    _hovered_cell = cell.duplicate(true)
    if not _area_request_id.is_empty():
        _state.cancel_pending(_area_request_id)
    _area_request_id = _state.request_preview(
        "spatial.area",
        {"shape": _debug_shape_payload(cell)},
        "v07-area:%s:%d:%d" % [
            _debug_shape_kind(),
            int(cell.get("x", 0)),
            int(cell.get("y", 0)),
        ],
    )
    _controller.register_mode_request(_area_request_id)
    _hud.set_preview_text(
        "%s origin %d,%d · direction %s · engine computes area membership" % [
            _debug_shape_kind().capitalize(),
            int(cell.get("x", 0)),
            int(cell.get("y", 0)),
            _direction_text(_debug_shape_direction),
        ]
    )


func _debug_shape_payload(cell: Dictionary) -> Dictionary:
    match _debug_shape_kind():
        "cylinder":
            return {
                "kind": "cylinder",
                "center": cell.duplicate(true),
                "radius_feet": 10,
                "height_feet": 10,
            }
        "cone":
            return {
                "kind": "cone",
                "origin": cell.duplicate(true),
                "direction": {
                    "x": _debug_shape_direction.x,
                    "y": _debug_shape_direction.y,
                },
                "length_feet": 15,
                "angle_degrees": 90,
            }
        "line":
            return {
                "kind": "line",
                "origin": cell.duplicate(true),
                "direction": {
                    "x": _debug_shape_direction.x,
                    "y": _debug_shape_direction.y,
                },
                "length_feet": 20,
                "width_feet": 5,
            }
        _:
            return {
                "kind": "sphere",
                "center": cell.duplicate(true),
                "radius_feet": 10,
            }


func _debug_shape_kind() -> String:
    return str(DEBUG_SHAPE_KINDS[_debug_shape_index])


func _shape_origin() -> Dictionary:
    if not _hovered_cell.is_empty():
        return _hovered_cell.duplicate(true)
    if _state == null:
        return {}
    var actor := _actor_data(_state.interaction.selected_actor_id())
    var position_value: Variant = actor.get("position", {})
    return (
        (position_value as Dictionary).duplicate(true)
        if typeof(position_value) == TYPE_DICTIONARY
        else {}
    )


func _direction_text(direction: Vector2) -> String:
    if absf(direction.x) >= absf(direction.y):
        return "east" if direction.x >= 0.0 else "west"
    return "south" if direction.y >= 0.0 else "north"


func _refresh_active_preview_after_state_change() -> void:
    if _state == null or _controller == null:
        return
    var sequence := _state.authoritative.sequence()
    if sequence == _preview_authority_sequence:
        return
    _preview_authority_sequence = sequence
    var mode := _controller.current_mode()
    if mode == InteractionModes.Mode.MOVE:
        if not _armed_cell.is_empty():
            _request_path(_armed_cell)
        elif not _hovered_cell.is_empty():
            _request_path(_hovered_cell)
        else:
            _request_reachable_for_selected()
    elif mode == InteractionModes.Mode.TARGET:
        var target_id := _state.interaction.targeted_actor_id()
        if not target_id.is_empty():
            _request_attack_preview(target_id)
    elif mode == InteractionModes.Mode.SHAPE_PREVIEW and not _hovered_cell.is_empty():
        _request_area_at(_hovered_cell)


func _on_query_completed(
    correlation_id: String,
    _generation: int,
    payload: Dictionary,
) -> void:
    if correlation_id.begins_with("v07-actions:"):
        _hud.apply_actions(payload)


func _on_preview_completed(
    correlation_id: String,
    _generation: int,
    payload: Dictionary,
) -> void:
    if correlation_id.begins_with("v07-reachable:"):
        _reachable_request_id = ""
        _overlay.show_reachable(payload)
        return
    if correlation_id.begins_with("v07-path:"):
        _path_request_id = ""
        _apply_path_preview(payload)
        return
    if correlation_id.begins_with("v07-attack:"):
        _target_request_id = ""
        _apply_attack_preview(payload)
        return
    if correlation_id.begins_with("v07-area:"):
        _area_request_id = ""
        _overlay.show_area(payload)
        var ids: Variant = payload.get("entity_ids", [])
        _hud.set_preview_text(
            "%s · authoritative area members: %s" % [
                _debug_shape_kind().capitalize(),
                ids,
            ]
        )


func _apply_path_preview(payload: Dictionary) -> void:
    _overlay.show_path(payload)
    if not bool(payload.get("legal", false)):
        _armed_cell.clear()
        _hud.set_preview_text(str(payload.get("reason", "Destination is not legal")))
        return
    var path_value: Variant = payload.get("path", [])
    if typeof(path_value) != TYPE_ARRAY or (path_value as Array).is_empty():
        return
    var path: Array = path_value
    var last_value: Variant = path[path.size() - 1]
    if typeof(last_value) != TYPE_DICTIONARY:
        return
    _armed_cell = (last_value as Dictionary).duplicate(true)
    var actor_id := _state.interaction.selected_actor_id()
    var segment_text := _segment_cost_text(payload.get("segments", []))
    _hud.set_preview_text(
        "Path %d ft%s · select again or Confirm to move" % [
            int(payload.get("cost_feet", 0)),
            segment_text,
        ]
    )
    _controller.set_command_intent(
        _command(
            "tactical.move",
            actor_id,
            {"destination": _armed_cell, "movement_mode": "walk"},
        ),
        "v07-move:%d:%d:%d" % [
            _state.authoritative.sequence(),
            int(_armed_cell.get("x", 0)),
            int(_armed_cell.get("y", 0)),
        ],
    )


func _segment_cost_text(value: Variant) -> String:
    if typeof(value) != TYPE_ARRAY or (value as Array).is_empty():
        return ""
    var rows: Array[String] = []
    for raw in value:
        if typeof(raw) != TYPE_DICTIONARY:
            continue
        var segment: Dictionary = raw
        rows.append(
            "%s %d ft" % [
                str(segment.get("terrain_id", segment.get("reason", "segment"))),
                int(segment.get("cost_feet", 0)),
            ]
        )
    return " · %s" % ", ".join(rows) if not rows.is_empty() else ""


func _apply_attack_preview(payload: Dictionary) -> void:
    var attacker_id := str(payload.get("attacker_id", ""))
    var target_id := str(payload.get("target_id", ""))
    var attacker := actor_view(attacker_id)
    var target := actor_view(target_id)
    if attacker != null and target != null:
        _overlay.show_target_line(attacker.global_position, target.global_position, payload)
    var legal := bool(payload.get("legal", false))
    var detail := "Distance %s ft · LOS %s · cover %s" % [
        payload.get("distance_feet", "?"),
        "clear" if bool(payload.get("visible", false)) else "blocked",
        str(payload.get("cover", "none")),
    ]
    if not legal:
        _armed_target = ""
        _hud.set_preview_text("%s\n%s" % [str(payload.get("reason", "Illegal target")), detail])
        return
    _armed_target = target_id
    _hud.set_preview_text("%s\nSelect again or Confirm to strike" % detail)
    _controller.set_command_intent(
        _command("tactical.attack", attacker_id, {"target_id": target_id}),
        "v07-strike:%d:%s" % [_state.authoritative.sequence(), target_id],
    )


func _on_authoritative_changed(_sequence: int) -> void:
    _refresh_from_authority()


func _on_command_completed(
    _correlation_id: String,
    accepted: bool,
    user_message: String,
    debug_detail: String,
) -> void:
    if accepted:
        _hud.set_preview_text("Authoritative command accepted")
    else:
        _hud.set_error(user_message, debug_detail)
    _request_actions()


func _on_selection_changed(_actor_id: String, _generation: int) -> void:
    _refresh_indicators()
    _hud.apply_tactical_state(
        _tactical,
        _state.interaction.selected_actor_id(),
    )
    _request_actions()
    _refresh_occlusion()


func _on_hover_changed(_actor_id: String, _generation: int) -> void:
    _refresh_indicators()


func _on_interaction_mode_changed(mode: int, _generation: int) -> void:
    if mode not in [
        InteractionModes.Mode.MOVE,
        InteractionModes.Mode.TARGET,
        InteractionModes.Mode.SHAPE_PREVIEW,
    ]:
        _hovered_cell.clear()
        _overlay.clear_all()


func _on_presentation_options_changed() -> void:
    if _state == null:
        return
    _camera_rig.set_reduced_motion(_state.presentation.reduced_motion())
    _refresh_debug_layers()


func _on_actor_emphasis_requested(actor_id: String) -> void:
    var view := actor_view(actor_id)
    if view == null:
        return
    view.set_hovered(true)
    get_tree().create_timer(0.35).timeout.connect(
        func() -> void:
            if is_instance_valid(view):
                view.set_hovered(
                    _state != null
                    and _state.interaction.hovered_actor_id() == actor_id
                )
    )


func _on_vfx_cue_requested(
    cue_id: String,
    actor_id: String,
    payload: Dictionary,
) -> void:
    if _state == null:
        return
    var view := actor_view(actor_id)
    if view == null:
        return
    _vfx_presenter.present(
        cue_id,
        view,
        payload,
        _state.presentation.reduced_motion(),
    )


func _focus_selected_or_current() -> void:
    if _state == null:
        return
    var actor_id := _state.interaction.selected_actor_id()
    if actor_id.is_empty():
        actor_id = str(_tactical.get("current_actor_id", ""))
    var view := actor_view(actor_id)
    if view != null:
        _camera_rig.focus_world_position(view.global_position)
        _refresh_occlusion()


func _cycle_selection() -> void:
    if _state == null:
        return
    var ids := _actor_ids(false)
    if ids.is_empty():
        return
    var selected := _state.interaction.selected_actor_id()
    var index := ids.find(selected)
    _state.interaction.set_selected_actor(ids[(index + 1) % ids.size()])


func _cycle_target() -> void:
    if _state == null:
        return
    var selected := _state.interaction.selected_actor_id()
    var ids := _actor_ids(true)
    ids = ids.filter(func(value: String) -> bool: return value != selected)
    if ids.is_empty():
        _hud.set_preview_text("No other authoritative target candidates are present")
        return
    var current := _state.interaction.targeted_actor_id()
    var index := ids.find(current)
    var next_target := ids[(index + 1) % ids.size()]
    _state.interaction.set_hovered_actor(next_target)
    _request_attack_preview(next_target)


func _actor_ids(living_only: bool) -> Array[String]:
    var ids: Array[String] = []
    var actors_value: Variant = _tactical.get("actors", [])
    if typeof(actors_value) != TYPE_ARRAY:
        return ids
    for actor_value in actors_value:
        if typeof(actor_value) != TYPE_DICTIONARY:
            continue
        var actor: Dictionary = actor_value
        if living_only and str(actor.get("life_state", "conscious")) == "dead":
            continue
        var actor_id := str(actor.get("actor_id", ""))
        if not actor_id.is_empty():
            ids.append(actor_id)
    return ids


func _refresh_occlusion() -> void:
    if _camera == null:
        return
    var actor_id := ""
    if _state != null:
        actor_id = _state.interaction.selected_actor_id()
    if actor_id.is_empty():
        actor_id = str(_tactical.get("current_actor_id", ""))
    var view := actor_view(actor_id)
    if view == null:
        _occlusion.clear()
        return
    _occlusion.refresh(_camera.global_position, view.global_position)


func _pick(pointer: Vector2) -> Dictionary:
    if _camera == null or get_world_3d() == null:
        return {}
    var origin := _camera.project_ray_origin(pointer)
    var direction := _camera.project_ray_normal(pointer)
    var query := PhysicsRayQueryParameters3D.create(origin, origin + direction * 200.0)
    query.collide_with_areas = false
    query.collide_with_bodies = true
    # Occlusion blockers are presentation-only MeshInstance3D nodes, deliberately
    # without collision bodies. Fading/hidden foreground geometry therefore cannot
    # intercept actor or tactical-surface picking.
    return get_world_3d().direct_space_state.intersect_ray(query)


func _actor_from_hit(hit: Dictionary) -> String:
    var collider: Variant = hit.get("collider")
    if collider is Object and (collider as Object).has_meta("actor_id"):
        return str((collider as Object).get_meta("actor_id"))
    return ""


func _cell_from_hit(hit: Dictionary) -> Dictionary:
    var collider: Variant = hit.get("collider")
    if collider is Object:
        var object := collider as Object
        if object.has_meta("grid_x") and object.has_meta("grid_y"):
            return {
                "x": int(object.get_meta("grid_x")),
                "y": int(object.get_meta("grid_y")),
            }
    return {}


func _command(
    command_type: String,
    actor_id: String,
    payload: Dictionary,
) -> Dictionary:
    _command_counter += 1
    var state_view := _state.authoritative.state_view()
    return {
        "command_id": "command:v07-%06d" % _command_counter,
        "campaign_id": str(state_view.get("campaign_id", "")),
        "session_id": str(state_view.get("session_id", "")),
        "command_type": command_type,
        "payload": payload.duplicate(true),
        "version": 1,
        "actor_id": actor_id,
        "expected_sequence": _state.authoritative.sequence(),
    }


func _actor_data(actor_id: String) -> Dictionary:
    if actor_id.is_empty():
        return {}
    var actors_value: Variant = _tactical.get("actors", [])
    if typeof(actors_value) != TYPE_ARRAY:
        return {}
    for actor_value in actors_value:
        if typeof(actor_value) != TYPE_DICTIONARY:
            continue
        var actor: Dictionary = actor_value
        if str(actor.get("actor_id", "")) == actor_id:
            return actor
    return {}


func _cancel_scene_preview_requests() -> void:
    if _state == null:
        _path_request_id = ""
        _reachable_request_id = ""
        _target_request_id = ""
        _area_request_id = ""
        return
    for request_id in [
        _path_request_id,
        _reachable_request_id,
        _target_request_id,
        _area_request_id,
    ]:
        if not request_id.is_empty():
            _state.cancel_pending(request_id)
    _path_request_id = ""
    _reachable_request_id = ""
    _target_request_id = ""
    _area_request_id = ""


func _unbind_state() -> void:
    _event_presenter.unbind_state()
    if _state == null:
        return
    _cancel_scene_preview_requests()
    _disconnect(_state.authoritative_changed, _on_authoritative_changed)
    _disconnect(_state.query_completed, _on_query_completed)
    _disconnect(_state.preview_completed, _on_preview_completed)
    _disconnect(_state.command_completed, _on_command_completed)
    _disconnect(_state.interaction.selection_changed, _on_selection_changed)
    _disconnect(_state.interaction.hover_changed, _on_hover_changed)
    _disconnect(_state.interaction.mode_changed, _on_interaction_mode_changed)
    _disconnect(_state.presentation.options_changed, _on_presentation_options_changed)
    _state = null


func _unbind_controller() -> void:
    if _controller == null:
        return
    _disconnect(_controller.camera_action_requested, _on_camera_action_requested)
    _disconnect(_controller.select_requested, _on_select_requested)
    _disconnect(_controller.confirm_requested, _on_confirm_requested)
    _disconnect(_controller.context_requested, _on_context_requested)
    _disconnect(_controller.mode_changed, _on_controller_mode_changed)
    _disconnect(_controller.command_intent_rejected, _on_intent_rejected)
    _controller = null


func _disconnect(signal_value: Signal, callable: Callable) -> void:
    if signal_value.is_connected(callable):
        signal_value.disconnect(callable)
