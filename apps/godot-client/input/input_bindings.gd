class_name ClientInputBindings
extends RefCounted

const ClientInputActions = preload("res://input/input_actions.gd")

signal binding_changed(action: StringName)

const SETTINGS_PATH := "user://input_bindings.cfg"
const SECTION := "bindings"
const DEFAULT_DEADZONE := 0.2


func install_defaults() -> void:
    for action in ClientInputActions.all_actions():
        if not InputMap.has_action(action):
            InputMap.add_action(action, DEFAULT_DEADZONE)
        else:
            InputMap.action_set_deadzone(action, DEFAULT_DEADZONE)
        if InputMap.action_get_events(action).is_empty():
            _replace_events(action, _default_events(action), false)


func action_events(action: StringName) -> Array[InputEvent]:
    var result: Array[InputEvent] = []
    if not ClientInputActions.is_known(action) or not InputMap.has_action(action):
        return result
    for raw_event in InputMap.action_get_events(action):
        if raw_event is InputEvent:
            result.append((raw_event as InputEvent).duplicate(true))
    return result


func replace_events(
    action: StringName,
    events: Array[InputEvent],
    persist: bool = false,
) -> bool:
    if not ClientInputActions.is_known(action):
        return false
    install_defaults()
    var copies: Array[InputEvent] = []
    for event in events:
        if event == null:
            return false
        copies.append(event.duplicate(true))
    _replace_events(action, copies, true)
    if persist:
        save_overrides()
    return true


func reset_action(action: StringName, persist: bool = false) -> bool:
    if not ClientInputActions.is_known(action):
        return false
    install_defaults()
    _replace_events(action, _default_events(action), true)
    if persist:
        save_overrides()
    return true


func reset_all(persist: bool = false) -> void:
    install_defaults()
    for action in ClientInputActions.all_actions():
        _replace_events(action, _default_events(action), true)
    if persist:
        save_overrides()


func descriptors(action: StringName) -> Array:
    var result: Array = []
    for event in action_events(action):
        var descriptor := _event_to_descriptor(event)
        if not descriptor.is_empty():
            result.append(descriptor)
    return result


func apply_descriptors(
    action: StringName,
    raw_descriptors: Array,
    persist: bool = false,
) -> bool:
    if not ClientInputActions.is_known(action):
        return false
    var events: Array[InputEvent] = []
    for raw_descriptor in raw_descriptors:
        if typeof(raw_descriptor) != TYPE_DICTIONARY:
            return false
        var event := _descriptor_to_event(raw_descriptor)
        if event == null:
            return false
        events.append(event)
    install_defaults()
    _replace_events(action, events, true)
    if persist:
        save_overrides()
    return true


func save_overrides() -> bool:
    var config := ConfigFile.new()
    for action in ClientInputActions.all_actions():
        config.set_value(SECTION, str(action), descriptors(action))
    var result := config.save(SETTINGS_PATH)
    if result != OK:
        push_warning("Unable to save client input bindings: %s" % error_string(result))
        return false
    return true


func load_overrides() -> bool:
    install_defaults()
    var config := ConfigFile.new()
    var result := config.load(SETTINGS_PATH)
    if result == ERR_FILE_NOT_FOUND:
        return true
    if result != OK:
        push_warning("Unable to load client input bindings: %s" % error_string(result))
        return false
    for action in ClientInputActions.all_actions():
        if not config.has_section_key(SECTION, str(action)):
            continue
        var raw_value: Variant = config.get_value(SECTION, str(action), [])
        if typeof(raw_value) != TYPE_ARRAY:
            push_warning("Ignoring malformed binding override for %s" % action)
            continue
        var raw_descriptors: Array = raw_value
        if not apply_descriptors(action, raw_descriptors, false):
            push_warning("Ignoring unsupported binding override for %s" % action)
    return true


func _replace_events(
    action: StringName,
    events: Array[InputEvent],
    emit_change: bool,
) -> void:
    InputMap.action_erase_events(action)
    for event in events:
        InputMap.action_add_event(action, event)
    if emit_change:
        binding_changed.emit(action)


func _default_events(action: StringName) -> Array[InputEvent]:
    match action:
        ClientInputActions.CAMERA_PAN_UP:
            return _event_list([
                _key(KEY_W),
                _key(KEY_UP),
                _joy_button(JOY_BUTTON_DPAD_UP),
                _joy_axis(JOY_AXIS_LEFT_Y, -1.0),
            ])
        ClientInputActions.CAMERA_PAN_DOWN:
            return _event_list([
                _key(KEY_S),
                _key(KEY_DOWN),
                _joy_button(JOY_BUTTON_DPAD_DOWN),
                _joy_axis(JOY_AXIS_LEFT_Y, 1.0),
            ])
        ClientInputActions.CAMERA_PAN_LEFT:
            return _event_list([
                _key(KEY_A),
                _key(KEY_LEFT),
                _joy_button(JOY_BUTTON_DPAD_LEFT),
                _joy_axis(JOY_AXIS_LEFT_X, -1.0),
            ])
        ClientInputActions.CAMERA_PAN_RIGHT:
            return _event_list([
                _key(KEY_D),
                _key(KEY_RIGHT),
                _joy_button(JOY_BUTTON_DPAD_RIGHT),
                _joy_axis(JOY_AXIS_LEFT_X, 1.0),
            ])
        ClientInputActions.CAMERA_ZOOM_IN:
            return _event_list([
                _key(KEY_EQUAL),
                _mouse_button(MOUSE_BUTTON_WHEEL_UP),
                _joy_button(JOY_BUTTON_RIGHT_STICK),
            ])
        ClientInputActions.CAMERA_ZOOM_OUT:
            return _event_list([
                _key(KEY_MINUS),
                _mouse_button(MOUSE_BUTTON_WHEEL_DOWN),
                _joy_button(JOY_BUTTON_LEFT_STICK),
            ])
        ClientInputActions.CAMERA_ROTATE_LEFT:
            return _event_list([
                _key(KEY_Q),
                _joy_button(JOY_BUTTON_LEFT_SHOULDER),
            ])
        ClientInputActions.CAMERA_ROTATE_RIGHT:
            return _event_list([
                _key(KEY_E),
                _joy_button(JOY_BUTTON_RIGHT_SHOULDER),
            ])
        ClientInputActions.CAMERA_FOCUS:
            return _event_list([_key(KEY_F), _joy_button(JOY_BUTTON_Y)])
        ClientInputActions.SELECT:
            return _event_list([
                _mouse_button(MOUSE_BUTTON_LEFT),
                _joy_button(JOY_BUTTON_A),
            ])
        ClientInputActions.CONFIRM:
            return _event_list([
                _key(KEY_ENTER),
                _key(KEY_SPACE),
                _joy_button(JOY_BUTTON_A),
            ])
        ClientInputActions.CANCEL:
            return _event_list([
                _key(KEY_ESCAPE),
                _mouse_button(MOUSE_BUTTON_RIGHT),
                _joy_button(JOY_BUTTON_B),
            ])
        ClientInputActions.CONTEXT:
            return _event_list([
                _key(KEY_C),
                _mouse_button(MOUSE_BUTTON_MIDDLE),
                _joy_button(JOY_BUTTON_X),
            ])
        _:
            return []


func _event_list(values: Array) -> Array[InputEvent]:
    var result: Array[InputEvent] = []
    for value in values:
        if value is InputEvent:
            result.append(value as InputEvent)
    return result


func _key(physical_keycode: int) -> InputEventKey:
    var event := InputEventKey.new()
    event.physical_keycode = physical_keycode
    return event


func _mouse_button(button_index: int) -> InputEventMouseButton:
    var event := InputEventMouseButton.new()
    event.button_index = button_index
    return event


func _joy_button(button_index: int) -> InputEventJoypadButton:
    var event := InputEventJoypadButton.new()
    event.device = -1
    event.button_index = button_index
    return event


func _joy_axis(axis: int, axis_value: float) -> InputEventJoypadMotion:
    var event := InputEventJoypadMotion.new()
    event.device = -1
    event.axis = axis
    event.axis_value = axis_value
    return event


func _event_to_descriptor(event: InputEvent) -> Dictionary:
    if event is InputEventKey:
        var key_event := event as InputEventKey
        return {
            "type": "key",
            "physical_keycode": int(key_event.physical_keycode),
            "device": key_event.device,
        }
    if event is InputEventMouseButton:
        var mouse_event := event as InputEventMouseButton
        return {
            "type": "mouse_button",
            "button_index": mouse_event.button_index,
            "device": mouse_event.device,
        }
    if event is InputEventJoypadButton:
        var joy_button_event := event as InputEventJoypadButton
        return {
            "type": "joy_button",
            "button_index": joy_button_event.button_index,
            "device": joy_button_event.device,
        }
    if event is InputEventJoypadMotion:
        var joy_motion_event := event as InputEventJoypadMotion
        return {
            "type": "joy_motion",
            "axis": joy_motion_event.axis,
            "axis_value": joy_motion_event.axis_value,
            "device": joy_motion_event.device,
        }
    return {}


func _descriptor_to_event(descriptor: Dictionary) -> InputEvent:
    var event_type := str(descriptor.get("type", ""))
    match event_type:
        "key":
            if not descriptor.has("physical_keycode"):
                return null
            var key_event := _key(int(descriptor["physical_keycode"]))
            key_event.device = int(descriptor.get("device", 0))
            return key_event
        "mouse_button":
            if not descriptor.has("button_index"):
                return null
            var mouse_event := _mouse_button(int(descriptor["button_index"]))
            mouse_event.device = int(descriptor.get("device", 0))
            return mouse_event
        "joy_button":
            if not descriptor.has("button_index"):
                return null
            var joy_button_event := _joy_button(int(descriptor["button_index"]))
            joy_button_event.device = int(descriptor.get("device", -1))
            return joy_button_event
        "joy_motion":
            if not descriptor.has("axis") or not descriptor.has("axis_value"):
                return null
            var axis_value := float(descriptor["axis_value"])
            if axis_value < -1.0 or axis_value > 1.0 or is_zero_approx(axis_value):
                return null
            var joy_motion_event := _joy_axis(int(descriptor["axis"]), axis_value)
            joy_motion_event.device = int(descriptor.get("device", -1))
            return joy_motion_event
        _:
            return null
