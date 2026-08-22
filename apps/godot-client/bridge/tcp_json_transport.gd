class_name TcpJsonTransport
extends EngineTransport

const Protocol = preload("res://bridge/bridge_protocol.gd")

var _peer := StreamPeerTCP.new()
var _host := "127.0.0.1"
var _port := 4765
var _receive_buffer := PackedByteArray()
var _last_status := StreamPeerTCP.STATUS_NONE
var _was_connected := false


func start(config: Dictionary = {}) -> Error:
    if _peer.get_status() != StreamPeerTCP.STATUS_NONE:
        return ERR_ALREADY_IN_USE
    if config.has("host"):
        if typeof(config["host"]) != TYPE_STRING or str(config["host"]).is_empty():
            return ERR_INVALID_PARAMETER
        _host = str(config["host"])
    if config.has("port"):
        if typeof(config["port"]) != TYPE_INT:
            return ERR_INVALID_PARAMETER
        _port = int(config["port"])
    if _port < 1 or _port > 65535:
        return ERR_INVALID_PARAMETER
    _receive_buffer.clear()
    _last_status = StreamPeerTCP.STATUS_NONE
    _was_connected = false
    return _peer.connect_to_host(_host, _port)


func poll(_delta: float) -> void:
    _peer.poll()
    var status := _peer.get_status()
    if status != _last_status:
        _handle_status_change(status)
        _last_status = status
    if status != StreamPeerTCP.STATUS_CONNECTED:
        return
    _read_available()


func send(message: Dictionary) -> Error:
    if not is_connected():
        return ERR_UNCONFIGURED
    var validation_error := Protocol.validate_message(message)
    if not validation_error.is_empty():
        return ERR_INVALID_DATA
    var encoded := (JSON.stringify(message) + "\n").to_utf8_buffer()
    return _peer.put_data(encoded)


func stop() -> void:
    var notify := _was_connected
    _peer.disconnect_from_host()
    _receive_buffer.clear()
    _last_status = StreamPeerTCP.STATUS_NONE
    _was_connected = false
    if notify:
        disconnected.emit("transport stopped")


func is_connected() -> bool:
    return _peer.get_status() == StreamPeerTCP.STATUS_CONNECTED


func _handle_status_change(status: StreamPeerTCP.Status) -> void:
    if status == StreamPeerTCP.STATUS_CONNECTED:
        _was_connected = true
        connected.emit()
        return
    if _was_connected and status in [StreamPeerTCP.STATUS_NONE, StreamPeerTCP.STATUS_ERROR]:
        _was_connected = false
        disconnected.emit("tcp connection closed")
    if status == StreamPeerTCP.STATUS_ERROR:
        transport_error.emit(
            Protocol.ErrorCategory.TRANSPORT,
            "Engine connection failed",
            "TCP transport entered STATUS_ERROR for %s:%d" % [_host, _port],
        )


func _read_available() -> void:
    var available := _peer.get_available_bytes()
    if available <= 0:
        return
    var result := _peer.get_data(available)
    if int(result[0]) != OK:
        transport_error.emit(
            Protocol.ErrorCategory.TRANSPORT,
            "Engine connection read failed",
            "StreamPeerTCP.get_data returned error %s" % result[0],
        )
        return
    var bytes: PackedByteArray = result[1]
    _receive_buffer.append_array(bytes)
    _drain_lines()


func _drain_lines() -> void:
    while true:
        var newline_index := _receive_buffer.find(10)
        if newline_index < 0:
            return
        var line_bytes := _receive_buffer.slice(0, newline_index)
        _receive_buffer = _receive_buffer.slice(newline_index + 1)
        if line_bytes.is_empty():
            continue
        var parsed: Variant = JSON.parse_string(line_bytes.get_string_from_utf8())
        if typeof(parsed) != TYPE_DICTIONARY:
            transport_error.emit(
                Protocol.ErrorCategory.VALIDATION,
                "Received malformed engine message",
                "TCP line was not a JSON object",
            )
            continue
        var message: Dictionary = parsed
        message_received.emit(message)
