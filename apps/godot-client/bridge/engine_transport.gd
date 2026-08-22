class_name EngineTransport
extends RefCounted

signal connected
signal disconnected(reason: String)
signal message_received(message: Dictionary)
signal transport_error(category: int, user_message: String, debug_detail: String)


func start(_config: Dictionary = {}) -> Error:
    return ERR_UNAVAILABLE


func poll(_delta: float) -> void:
    pass


func send(_message: Dictionary) -> Error:
    return ERR_UNAVAILABLE


func cancel(_request_id: String) -> void:
    pass


func stop() -> void:
    pass


func is_connected() -> bool:
    return false
