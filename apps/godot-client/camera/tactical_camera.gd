class_name TacticalCameraController
extends Node3D

signal camera_state_changed(quarter_turn: int, zoom_size: float, focus: Vector3)

@export var pan_speed := 10.0
@export var min_zoom := 6.0
@export var max_zoom := 24.0
@export var zoom_step := 1.5
@export var smoothing := 10.0

var _quarter_turn := 0
var _target_focus := Vector3.ZERO
var _target_zoom := 14.0
var _bounds := Rect2(Vector2(-100.0, -100.0), Vector2(200.0, 200.0))
var _dragging := false
var _last_pointer := Vector2.ZERO
var _reduced_motion := false

@onready var _yaw: Node3D = $Yaw
@onready var _camera: Camera3D = $Yaw/Tilt/Camera3D


func _ready() -> void:
    _camera.projection = Camera3D.PROJECTION_ORTHOGONAL
    _target_zoom = clampf(_camera.size, min_zoom, max_zoom)
    _target_focus = global_position
    set_process(true)


func _process(delta: float) -> void:
    var pan_input := Vector2(
        Input.get_action_strength(ClientInputActions.CAMERA_PAN_RIGHT)
            - Input.get_action_strength(ClientInputActions.CAMERA_PAN_LEFT),
        Input.get_action_strength(ClientInputActions.CAMERA_PAN_DOWN)
            - Input.get_action_strength(ClientInputActions.CAMERA_PAN_UP),
    )
    if pan_input.length_squared() > 0.0:
        pan_input = pan_input.normalized()
        var yaw := _yaw.rotation.y
        var right := Vector3(cos(yaw), 0.0, -sin(yaw))
        var forward := Vector3(-sin(yaw), 0.0, -cos(yaw))
        _target_focus += (right * pan_input.x + forward * pan_input.y) * pan_speed * delta
        _target_focus = _clamped_focus(_target_focus)

    if _reduced_motion:
        global_position = _target_focus
        _camera.size = _target_zoom
        _yaw.rotation.y = _target_yaw()
        return
    var weight := 1.0 - exp(-smoothing * delta)
    global_position = global_position.lerp(_target_focus, weight)
    _camera.size = lerpf(_camera.size, _target_zoom, weight)
    _yaw.rotation.y = lerp_angle(_yaw.rotation.y, _target_yaw(), weight)


func handle_camera_action(action: StringName) -> void:
    match action:
        ClientInputActions.CAMERA_ZOOM_IN:
            set_zoom(_target_zoom - zoom_step)
        ClientInputActions.CAMERA_ZOOM_OUT:
            set_zoom(_target_zoom + zoom_step)
        ClientInputActions.CAMERA_ROTATE_LEFT:
            rotate_quarter(-1)
        ClientInputActions.CAMERA_ROTATE_RIGHT:
            rotate_quarter(1)
        _:
            pass


func set_map_bounds(bounds: Rect2) -> void:
    _bounds = bounds
    _target_focus = _clamped_focus(_target_focus)


func set_reduced_motion(enabled: bool) -> void:
    _reduced_motion = enabled


func focus_world_position(world_position: Vector3) -> void:
    _target_focus = _clamped_focus(Vector3(world_position.x, 0.0, world_position.z))
    if _reduced_motion:
        global_position = _target_focus
    camera_state_changed.emit(_quarter_turn, _target_zoom, _target_focus)


func set_zoom(size: float) -> void:
    _target_zoom = clampf(size, min_zoom, max_zoom)
    if _reduced_motion:
        _camera.size = _target_zoom
    camera_state_changed.emit(_quarter_turn, _target_zoom, _target_focus)


func rotate_quarter(direction: int) -> void:
    if direction == 0:
        return
    _quarter_turn = posmod(_quarter_turn + signi(direction), 4)
    if _reduced_motion:
        _yaw.rotation.y = _target_yaw()
    camera_state_changed.emit(_quarter_turn, _target_zoom, _target_focus)


func quarter_turn() -> int:
    return _quarter_turn


func zoom_size() -> float:
    return _target_zoom


func focus_position() -> Vector3:
    return _target_focus


func _unhandled_input(event: InputEvent) -> void:
    if event is InputEventMouseButton:
        var button := event as InputEventMouseButton
        if button.button_index == MOUSE_BUTTON_MIDDLE:
            _dragging = button.pressed
            _last_pointer = button.position
            if _dragging:
                get_viewport().set_input_as_handled()
    elif event is InputEventMouseMotion and _dragging:
        var motion := event as InputEventMouseMotion
        var delta_pixels := motion.position - _last_pointer
        _last_pointer = motion.position
        var scale := _target_zoom / maxf(get_viewport().get_visible_rect().size.y, 1.0)
        var yaw := _yaw.rotation.y
        var right := Vector3(cos(yaw), 0.0, -sin(yaw))
        var forward := Vector3(-sin(yaw), 0.0, -cos(yaw))
        _target_focus -= right * delta_pixels.x * scale
        _target_focus -= forward * delta_pixels.y * scale
        _target_focus = _clamped_focus(_target_focus)
        get_viewport().set_input_as_handled()


func _target_yaw() -> float:
    return deg_to_rad(45.0 + float(_quarter_turn * 90))


func _clamped_focus(value: Vector3) -> Vector3:
    return Vector3(
        clampf(value.x, _bounds.position.x, _bounds.end.x),
        value.y,
        clampf(value.z, _bounds.position.y, _bounds.end.y),
    )
