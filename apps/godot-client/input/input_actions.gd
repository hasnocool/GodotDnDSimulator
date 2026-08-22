class_name ClientInputActions
extends RefCounted

const CAMERA_PAN_UP: StringName = &"camera_pan_up"
const CAMERA_PAN_DOWN: StringName = &"camera_pan_down"
const CAMERA_PAN_LEFT: StringName = &"camera_pan_left"
const CAMERA_PAN_RIGHT: StringName = &"camera_pan_right"
const CAMERA_ZOOM_IN: StringName = &"camera_zoom_in"
const CAMERA_ZOOM_OUT: StringName = &"camera_zoom_out"
const CAMERA_ROTATE_LEFT: StringName = &"camera_rotate_left"
const CAMERA_ROTATE_RIGHT: StringName = &"camera_rotate_right"
const CAMERA_FOCUS: StringName = &"camera_focus"

const SELECT: StringName = &"interaction_select"
const CONFIRM: StringName = &"interaction_confirm"
const CANCEL: StringName = &"interaction_cancel"
const CONTEXT: StringName = &"interaction_context"


static func all_actions() -> Array[StringName]:
    return [
        CAMERA_PAN_UP,
        CAMERA_PAN_DOWN,
        CAMERA_PAN_LEFT,
        CAMERA_PAN_RIGHT,
        CAMERA_ZOOM_IN,
        CAMERA_ZOOM_OUT,
        CAMERA_ROTATE_LEFT,
        CAMERA_ROTATE_RIGHT,
        CAMERA_FOCUS,
        SELECT,
        CONFIRM,
        CANCEL,
        CONTEXT,
    ]


static func camera_actions() -> Array[StringName]:
    return [
        CAMERA_PAN_UP,
        CAMERA_PAN_DOWN,
        CAMERA_PAN_LEFT,
        CAMERA_PAN_RIGHT,
        CAMERA_ZOOM_IN,
        CAMERA_ZOOM_OUT,
        CAMERA_ROTATE_LEFT,
        CAMERA_ROTATE_RIGHT,
        CAMERA_FOCUS,
    ]


static func tactical_actions() -> Array[StringName]:
    return [SELECT, CONFIRM, CANCEL, CONTEXT]


static func is_known(action: StringName) -> bool:
    return all_actions().has(action)


static func is_camera_action(action: StringName) -> bool:
    return camera_actions().has(action)
