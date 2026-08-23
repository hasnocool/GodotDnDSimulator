extends Node

const DEFAULT_PORT := 4766
const MAX_REQUEST_BYTES := 262144
const MAX_CLIENTS := 4
const MAX_SNAPSHOT_CONTROLS := 1200
const SCREENSHOT_DIRECTORY := "user://logs/screenshots"

var _enabled := false
var _port := DEFAULT_PORT
var _token := ""
var _server := TCPServer.new()
var _connections: Array[Dictionary] = []


func _ready() -> void:
    _enabled = _automation_requested()
    if not _enabled:
        set_process(false)
        return
    _port = _configured_port()
    _token = OS.get_environment("GODOT_DND_UI_AUTOMATION_TOKEN")
    var error := _server.listen(_port, "127.0.0.1")
    if error != OK:
        _enabled = false
        set_process(false)
        ClientLog.write(
            "automation",
            "Unable to start UI automation API",
            "127.0.0.1:%d: %s" % [_port, error_string(error)],
            "error",
        )
        return
    ClientLog.write(
        "automation",
        "UI automation API listening",
        "127.0.0.1:%d token_required=%s" % [_port, not _token.is_empty()],
    )


func _exit_tree() -> void:
    for connection in _connections:
        var peer := connection.get("peer") as StreamPeerTCP
        if peer != null:
            peer.disconnect_from_host()
    _connections.clear()
    _server.stop()


func _process(_delta: float) -> void:
    _accept_connections()
    for index in range(_connections.size() - 1, -1, -1):
        if not _poll_connection(index):
            _connections.remove_at(index)


func enabled() -> bool:
    return _enabled


func port() -> int:
    return _port


func dispatch_for_test(method: String, params: Dictionary = {}) -> Dictionary:
    return _dispatch(method, params)


func _automation_requested() -> bool:
    if (
        OS.has_environment("GODOT_DND_UI_AUTOMATION")
        and OS.get_environment("GODOT_DND_UI_AUTOMATION") == "1"
    ):
        return true
    return OS.get_cmdline_user_args().has("--ui-automation")


func _configured_port() -> int:
    if not OS.has_environment("GODOT_DND_UI_AUTOMATION_PORT"):
        return DEFAULT_PORT
    var value := OS.get_environment("GODOT_DND_UI_AUTOMATION_PORT")
    if not value.is_valid_int():
        return DEFAULT_PORT
    return clampi(value.to_int(), 1024, 65535)


func _accept_connections() -> void:
    while _server.is_connection_available():
        var peer := _server.take_connection()
        if peer == null:
            return
        if _connections.size() >= MAX_CLIENTS:
            peer.disconnect_from_host()
            continue
        _connections.append({"peer": peer, "buffer": ""})
        ClientLog.write("automation", "UI automation client connected")


func _poll_connection(index: int) -> bool:
    var connection := _connections[index]
    var peer := connection.get("peer") as StreamPeerTCP
    if peer == null:
        return false
    peer.poll()
    var status := peer.get_status()
    if status in [StreamPeerTCP.STATUS_NONE, StreamPeerTCP.STATUS_ERROR]:
        return false
    var available := peer.get_available_bytes()
    if available <= 0:
        return true
    var received := peer.get_data(available)
    if received.size() != 2 or int(received[0]) != OK:
        return false
    var bytes := received[1] as PackedByteArray
    var buffer := str(connection.get("buffer", "")) + bytes.get_string_from_utf8()
    if buffer.to_utf8_buffer().size() > MAX_REQUEST_BYTES * 2:
        _send_response(
            peer,
            _error_response("", "request_too_large", "Automation request buffer is too large"),
        )
        peer.disconnect_from_host()
        return false
    while true:
        var newline := buffer.find("\n")
        if newline < 0:
            break
        var line := buffer.substr(0, newline).strip_edges()
        buffer = buffer.substr(newline + 1)
        if line.is_empty():
            continue
        if line.to_utf8_buffer().size() > MAX_REQUEST_BYTES:
            _send_response(
                peer,
                _error_response("", "request_too_large", "Automation request is too large"),
            )
            continue
        _send_response(peer, _handle_line(line))
    connection["buffer"] = buffer
    return true


func _handle_line(line: String) -> Dictionary:
    var decoded: Variant = JSON.parse_string(line)
    if typeof(decoded) != TYPE_DICTIONARY:
        return _error_response("", "invalid_request", "Request must be a JSON object")
    var request: Dictionary = decoded
    var request_id := str(request.get("id", ""))
    if not _token.is_empty() and str(request.get("token", "")) != _token:
        ClientLog.write(
            "automation",
            "Rejected UI automation request",
            "invalid token",
            "warning",
            {"request_id": request_id},
        )
        return _error_response(request_id, "unauthorized", "Automation token is invalid")
    var method := str(request.get("method", ""))
    var params_value: Variant = request.get("params", {})
    if method.is_empty() or typeof(params_value) != TYPE_DICTIONARY:
        return _error_response(
            request_id,
            "invalid_request",
            "method must be non-empty and params must be an object",
        )
    ClientLog.write(
        "automation",
        "UI automation request",
        method,
        "debug",
        {"request_id": request_id},
    )
    var result := _dispatch(method, params_value)
    if not bool(result.get("ok", false)):
        result["id"] = request_id
        return result
    return {"id": request_id, "ok": true, "result": result.get("result", {})}


func _dispatch(method: String, params: Dictionary) -> Dictionary:
    match method:
        "automation.status":
            return _ok({
                "enabled": _enabled,
                "host": "127.0.0.1",
                "port": _port,
                "token_required": not _token.is_empty(),
                "client_log_path": ClientLog.disk_log_path(),
            })
        "ui.snapshot":
            return _ok(_ui_snapshot())
        "ui.inspect":
            var inspect_control := _control_at_path(str(params.get("path", "")))
            if inspect_control == null:
                return _automation_error("not_found", "Visible Control path was not found")
            return _ok(_control_row(inspect_control))
        "ui.focus":
            var focus_control := _control_at_path(str(params.get("path", "")))
            if focus_control == null:
                return _automation_error("not_found", "Visible Control path was not found")
            focus_control.grab_focus()
            return _ok({"path": str(focus_control.get_path()), "focused": focus_control.has_focus()})
        "ui.activate":
            var active_control := _control_at_path(str(params.get("path", "")))
            if active_control == null:
                return _automation_error("not_found", "Visible Control path was not found")
            if active_control is BaseButton and (active_control as BaseButton).disabled:
                return _automation_error("disabled", "Control is disabled")
            active_control.grab_focus()
            var rect := active_control.get_global_rect()
            _inject_mouse_click(rect.position + rect.size * 0.5)
            return _ok({"path": str(active_control.get_path()), "activated": true})
        "ui.click_at":
            var x_value: Variant = params.get("x")
            var y_value: Variant = params.get("y")
            if not _numeric(x_value) or not _numeric(y_value):
                return _automation_error("invalid_params", "x and y must be numeric")
            var point := Vector2(float(x_value), float(y_value))
            _inject_mouse_click(point)
            return _ok({"x": point.x, "y": point.y})
        "ui.set_text":
            return _set_text(params)
        "ui.input_action":
            return _input_action(params)
        "ui.logs":
            return _logs(params)
        "ui.screenshot":
            return _screenshot()
        _:
            return _automation_error("method_not_found", "Unknown UI automation method")


func _ui_snapshot() -> Dictionary:
    var controls: Array[Dictionary] = []
    var nodes := get_tree().root.find_children("*", "Control", true, false)
    for node in nodes:
        if controls.size() >= MAX_SNAPSHOT_CONTROLS:
            break
        var control := node as Control
        if control == null or not control.is_visible_in_tree():
            continue
        controls.append(_control_row(control))
    var focus := get_viewport().gui_get_focus_owner()
    var shell := _app_shell()
    var shell_state: Variant = null
    var shell_message := ""
    var authoritative_sequence: Variant = null
    if shell != null:
        if shell.has_method("shell_state"):
            shell_state = shell.call("shell_state")
        if shell.has_method("status_message"):
            shell_message = str(shell.call("status_message"))
        if shell.has_method("client_state"):
            var state: Variant = shell.call("client_state")
            if state != null:
                authoritative_sequence = state.authoritative.sequence()
    return {
        "viewport": {
            "width": get_viewport().get_visible_rect().size.x,
            "height": get_viewport().get_visible_rect().size.y,
        },
        "focus_path": "" if focus == null else str(focus.get_path()),
        "shell_state": shell_state,
        "shell_message": shell_message,
        "authoritative_sequence": authoritative_sequence,
        "control_count": controls.size(),
        "controls": controls,
        "client_log_path": ClientLog.disk_log_path(),
    }


func _control_row(control: Control) -> Dictionary:
    var rect := control.get_global_rect()
    return {
        "path": str(control.get_path()),
        "name": control.name,
        "class": control.get_class(),
        "text": _control_text(control),
        "disabled": _control_disabled(control),
        "focused": control.has_focus(),
        "focus_mode": control.focus_mode,
        "rect": {
            "x": rect.position.x,
            "y": rect.position.y,
            "width": rect.size.x,
            "height": rect.size.y,
        },
        "tooltip": control.tooltip_text,
    }


func _control_text(control: Control) -> String:
    if control is Label:
        return (control as Label).text
    if control is Button:
        return (control as Button).text
    if control is LineEdit:
        return (control as LineEdit).text
    if control is TextEdit:
        return (control as TextEdit).text
    if control is RichTextLabel:
        return (control as RichTextLabel).get_parsed_text()
    return ""


func _control_disabled(control: Control) -> bool:
    if control is BaseButton:
        return (control as BaseButton).disabled
    if control is LineEdit:
        return not (control as LineEdit).editable
    if control is TextEdit:
        return not (control as TextEdit).editable
    return false


func _control_at_path(path: String) -> Control:
    if path.is_empty() or not path.begins_with("/root/"):
        return null
    var node := get_tree().root.get_node_or_null(NodePath(path))
    if not (node is Control):
        return null
    var control := node as Control
    if not control.is_visible_in_tree():
        return null
    return control


func _set_text(params: Dictionary) -> Dictionary:
    var control := _control_at_path(str(params.get("path", "")))
    if control == null:
        return _automation_error("not_found", "Visible Control path was not found")
    var text_value: Variant = params.get("text")
    if typeof(text_value) != TYPE_STRING:
        return _automation_error("invalid_params", "text must be a string")
    if control is LineEdit:
        var line_edit := control as LineEdit
        if not line_edit.editable:
            return _automation_error("disabled", "LineEdit is not editable")
        line_edit.grab_focus()
        line_edit.text = str(text_value)
        line_edit.text_changed.emit(line_edit.text)
        return _ok({"path": str(line_edit.get_path()), "text": line_edit.text})
    if control is TextEdit:
        var text_edit := control as TextEdit
        if not text_edit.editable:
            return _automation_error("disabled", "TextEdit is not editable")
        text_edit.grab_focus()
        text_edit.text = str(text_value)
        text_edit.text_changed.emit()
        return _ok({"path": str(text_edit.get_path()), "text": text_edit.text})
    return _automation_error("invalid_control", "Control does not support editable text")


func _input_action(params: Dictionary) -> Dictionary:
    var action := str(params.get("action", ""))
    if action.is_empty() or not InputMap.has_action(action):
        return _automation_error("invalid_action", "Input action is not registered")
    var strength_value: Variant = params.get("strength", 1.0)
    if not _numeric(strength_value):
        return _automation_error("invalid_params", "strength must be numeric")
    var strength := clampf(float(strength_value), 0.0, 1.0)
    var pressed := InputEventAction.new()
    pressed.action = action
    pressed.pressed = true
    pressed.strength = strength
    get_viewport().push_input(pressed)
    var released := InputEventAction.new()
    released.action = action
    released.pressed = false
    released.strength = 0.0
    get_viewport().push_input(released)
    return _ok({"action": action, "strength": strength})


func _inject_mouse_click(position: Vector2) -> void:
    var motion := InputEventMouseMotion.new()
    motion.position = position
    get_viewport().push_input(motion)
    for pressed in [true, false]:
        var event := InputEventMouseButton.new()
        event.button_index = MOUSE_BUTTON_LEFT
        event.position = position
        event.pressed = pressed
        get_viewport().push_input(event)


func _logs(params: Dictionary) -> Dictionary:
    var category := str(params.get("category", ""))
    var limit := clampi(int(params.get("limit", 100)), 1, 500)
    var rows := ClientLog.entries(category)
    var start := maxi(0, rows.size() - limit)
    return _ok({
        "entries": rows.slice(start, rows.size()),
        "disk_log_path": ClientLog.disk_log_path(),
    })


func _screenshot() -> Dictionary:
    var directory_absolute := ProjectSettings.globalize_path(SCREENSHOT_DIRECTORY)
    var mkdir_error := DirAccess.make_dir_recursive_absolute(directory_absolute)
    if mkdir_error != OK and mkdir_error != ERR_ALREADY_EXISTS:
        return _automation_error("io_error", "Unable to create screenshot directory")
    var filename := "ui-%d.png" % int(Time.get_unix_time_from_system() * 1000.0)
    var user_path := "%s/%s" % [SCREENSHOT_DIRECTORY, filename]
    var absolute_path := ProjectSettings.globalize_path(user_path)
    var image := get_viewport().get_texture().get_image()
    var error := image.save_png(absolute_path)
    if error != OK:
        return _automation_error("io_error", "Unable to save UI screenshot")
    ClientLog.write(
        "automation",
        "UI screenshot captured",
        user_path,
        "debug",
    )
    return _ok({"path": user_path, "absolute_path": absolute_path})


func _app_shell() -> Node:
    return get_tree().root.find_child("AppShell", true, false)


func _numeric(value: Variant) -> bool:
    return typeof(value) in [TYPE_INT, TYPE_FLOAT]


func _send_response(peer: StreamPeerTCP, response: Dictionary) -> void:
    peer.put_data((JSON.stringify(response) + "\n").to_utf8_buffer())


func _ok(result: Dictionary) -> Dictionary:
    return {"ok": true, "result": result}


func _automation_error(code: String, message: String) -> Dictionary:
    return {"ok": false, "error": {"code": code, "message": message}}


func _error_response(request_id: String, code: String, message: String) -> Dictionary:
    return {
        "id": request_id,
        "ok": false,
        "error": {"code": code, "message": message},
    }
