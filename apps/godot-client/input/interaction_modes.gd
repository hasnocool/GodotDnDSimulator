class_name InteractionModes
extends RefCounted

enum Mode {
    INSPECT,
    SELECT,
    MOVE,
    TARGET,
    SHAPE_PREVIEW,
    UI_MODAL,
}


static func is_valid(mode: int) -> bool:
    return mode >= Mode.INSPECT and mode <= Mode.UI_MODAL


static func is_cancellable(mode: int) -> bool:
    return mode in [Mode.MOVE, Mode.TARGET, Mode.SHAPE_PREVIEW]


static func name_of(mode: int) -> String:
    match mode:
        Mode.INSPECT:
            return "inspect"
        Mode.SELECT:
            return "select"
        Mode.MOVE:
            return "move"
        Mode.TARGET:
            return "target"
        Mode.SHAPE_PREVIEW:
            return "shape_preview"
        Mode.UI_MODAL:
            return "ui_modal"
        _:
            return "unknown"
