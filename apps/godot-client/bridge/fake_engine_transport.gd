class_name FakeEngineTransport
extends EngineTransport

var sent_messages: Array[Dictionary] = []
var _incoming: Array[Dictionary] = []
var _connected := false


func start(_config: Dictionary = {}) -> Error:
    if _connected:
        return ERR_ALREADY_IN_USE
    _connected = true
    connected.emit()
    return OK


func poll(_delta: float) -> void:
    while not _incoming.is_empty():
        var message: Dictionary = _incoming.pop_front()
        message_received.emit(message.duplicate(true))


func send(message: Dictionary) -> Error:
    if not _connected:
        return ERR_UNCONFIGURED
    sent_messages.append(message.duplicate(true))
    return OK


func cancel(request_id: String) -> void:
    for index in range(_incoming.size() - 1, -1, -1):
        if str(_incoming[index].get("request_id", "")) == request_id:
            _incoming.remove_at(index)


func stop() -> void:
    if not _connected:
        return
    _connected = false
    disconnected.emit("transport stopped")


func _is_connected() -> bool:
    return _connected


func queue_message(message: Dictionary) -> void:
    _incoming.append(message.duplicate(true))


func simulate_disconnect(reason: String = "test disconnect") -> void:
    if not _connected:
        return
    _connected = false
    disconnected.emit(reason)


func simulate_reconnect() -> void:
    if _connected:
        return
    _connected = true
    connected.emit()
