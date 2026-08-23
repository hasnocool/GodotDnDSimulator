class_name BridgeProtocol
extends RefCounted

const PROTOCOL_NAME := "godot-dnd-bridge"
const PROTOCOL_VERSION := 1
const CLIENT_NAME := "godot-client"

static func _capabilities() -> PackedStringArray:
    return PackedStringArray([
        "commands.v1",
        "queries.v1",
        "previews.v1",
        "snapshots.v1",
        "events.v1",
        "request-cancel.v1",
        "request-generation.v1",
    ])

enum ErrorCategory {
    NONE,
    VALIDATION,
    CONFLICT,
    UNSUPPORTED,
    INCOMPATIBLE_VERSION,
    TRANSPORT,
    TIMEOUT,
    CANCELLED,
    STALE,
    INTERNAL,
}

const _ERROR_NAMES := {
    ErrorCategory.NONE: "none",
    ErrorCategory.VALIDATION: "validation",
    ErrorCategory.CONFLICT: "conflict",
    ErrorCategory.UNSUPPORTED: "unsupported",
    ErrorCategory.INCOMPATIBLE_VERSION: "incompatible_version",
    ErrorCategory.TRANSPORT: "transport",
    ErrorCategory.TIMEOUT: "timeout",
    ErrorCategory.CANCELLED: "cancelled",
    ErrorCategory.STALE: "stale",
    ErrorCategory.INTERNAL: "internal",
}


static func error_name(category: int) -> String:
    return str(_ERROR_NAMES.get(category, "internal"))


static func error_category(name: String) -> int:
    for category in _ERROR_NAMES:
        if _ERROR_NAMES[category] == name:
            return int(category)
    return ErrorCategory.INTERNAL


static func make_error(
    category: int,
    user_message: String,
    debug_detail: String = "",
) -> Dictionary:
    return {
        "category": error_name(category),
        "user_message": user_message,
        "debug_detail": debug_detail,
    }


static func make_envelope(
    kind: String,
    request_id: String,
    correlation_id: String,
    generation: int,
    payload: Dictionary = {},
) -> Dictionary:
    return {
        "bridge_version": PROTOCOL_VERSION,
        "kind": kind,
        "request_id": request_id,
        "correlation_id": correlation_id,
        "generation": generation,
        "payload": payload.duplicate(true),
    }


static func make_hello(request_id: String) -> Dictionary:
    return make_envelope(
        "bridge.hello",
        request_id,
        request_id,
        0,
        {
            "protocol": PROTOCOL_NAME,
            "client": CLIENT_NAME,
            "capabilities": _capabilities(),
        },
    )


static func make_command_request(
    request_id: String,
    correlation_id: String,
    generation: int,
    command: Dictionary,
) -> Dictionary:
    return make_envelope(
        "command.submit",
        request_id,
        correlation_id,
        generation,
        {"command": command.duplicate(true)},
    )


static func make_query_request(
    request_id: String,
    correlation_id: String,
    generation: int,
    query_type: String,
    query: Dictionary,
) -> Dictionary:
    return make_envelope(
        "query.request",
        request_id,
        correlation_id,
        generation,
        {
            "query_type": query_type,
            "query": query.duplicate(true),
        },
    )


static func make_preview_request(
    request_id: String,
    correlation_id: String,
    generation: int,
    preview_type: String,
    preview: Dictionary,
) -> Dictionary:
    return make_envelope(
        "preview.request",
        request_id,
        correlation_id,
        generation,
        {
            "preview_type": preview_type,
            "preview": preview.duplicate(true),
        },
    )


static func make_cancel_request(
    request_id: String,
    target_request_id: String,
    correlation_id: String,
    generation: int,
) -> Dictionary:
    return make_envelope(
        "request.cancel",
        request_id,
        correlation_id,
        generation,
        {"target_request_id": target_request_id},
    )


static func make_response(
    kind: String,
    request_id: String,
    correlation_id: String,
    generation: int,
    ok: bool,
    payload: Dictionary = {},
    error: Dictionary = {},
) -> Dictionary:
    var message := make_envelope(kind, request_id, correlation_id, generation, payload)
    message["ok"] = ok
    if not ok or not error.is_empty():
        message["error"] = error.duplicate(true)
    return message


static func validate_message(message: Dictionary) -> String:
    var required := [
        "bridge_version",
        "kind",
        "request_id",
        "correlation_id",
        "generation",
        "payload",
    ]
    for key in required:
        if not message.has(key):
            return "bridge message missing field: %s" % key
    if not _is_integral_number(message["bridge_version"]):
        return "bridge_version must be an integer"
    if typeof(message["kind"]) != TYPE_STRING or str(message["kind"]).is_empty():
        return "kind must be a non-empty string"
    if typeof(message["request_id"]) != TYPE_STRING:
        return "request_id must be a string"
    if typeof(message["correlation_id"]) != TYPE_STRING:
        return "correlation_id must be a string"
    if not _is_integral_number(message["generation"]) or int(message["generation"]) < 0:
        return "generation must be an integer >= 0"
    if typeof(message["payload"]) != TYPE_DICTIONARY:
        return "payload must be an object"
    if message.has("ok") and typeof(message["ok"]) != TYPE_BOOL:
        return "ok must be a boolean when present"
    if message.has("error") and typeof(message["error"]) != TYPE_DICTIONARY:
        return "error must be an object when present"
    return ""


static func _is_integral_number(value: Variant) -> bool:
    if typeof(value) == TYPE_INT:
        return true
    if typeof(value) != TYPE_FLOAT:
        return false
    var float_value := float(value)
    return is_finite(float_value) and float_value == floor(float_value)


static func validate_compatible(message: Dictionary) -> String:
    var validation_error := validate_message(message)
    if not validation_error.is_empty():
        return validation_error
    if int(message["bridge_version"]) != PROTOCOL_VERSION:
        return "unsupported bridge version %s; expected %s" % [
            message["bridge_version"],
            PROTOCOL_VERSION,
        ]
    return ""


static func response_error(message: Dictionary) -> Dictionary:
    var raw_error: Variant = message.get("error", {})
    if typeof(raw_error) != TYPE_DICTIONARY:
        return make_error(ErrorCategory.INTERNAL, "Invalid bridge error response")
    var error: Dictionary = raw_error
    return {
        "category": str(error.get("category", "internal")),
        "user_message": str(error.get("user_message", "Request failed")),
        "debug_detail": str(error.get("debug_detail", "")),
    }
