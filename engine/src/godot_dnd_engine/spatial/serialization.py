# engine/src/godot_dnd_engine/spatial/serialization.py
"""Canonical JSON/JSONL serialization for spatial movement facts."""

from __future__ import annotations

import json
from typing import Any

from ..errors import ValidationError
from .events import SpatialEvent, SpatialEventValue


def _json_value(value: SpatialEventValue) -> object:
    if isinstance(value, tuple):
        if all(isinstance(item, tuple) for item in value):
            return [list(item) for item in value]
        return list(value)
    return value


def event_to_dict(event: SpatialEvent) -> dict[str, object]:
    return {
        "sequence": event.sequence,
        "event_type": event.event_type,
        "entity_id": event.entity_id,
        "payload": {key: _json_value(value) for key, value in event.payload},
        "schema_version": event.schema_version,
    }


def serialize_event(event: SpatialEvent) -> str:
    return json.dumps(event_to_dict(event), sort_keys=True, separators=(",", ":"))


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _event_value(value: Any) -> SpatialEventValue:
    if value is None or isinstance(value, (str, bool)) or _is_int(value):
        return value
    if isinstance(value, list):
        if all(isinstance(item, str) for item in value):
            return tuple(value)
        if len(value) == 2 and all(_is_int(item) for item in value):
            return (value[0], value[1])
        if all(
            isinstance(item, list)
            and len(item) == 2
            and all(_is_int(coordinate) for coordinate in item)
            for item in value
        ):
            return tuple((item[0], item[1]) for item in value)
    raise ValidationError("spatial event payload contains an unsupported value")


def deserialize_event(value: str) -> SpatialEvent:
    try:
        raw: Any = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValidationError("serialized spatial event is not valid JSON") from exc
    if not isinstance(raw, dict):
        raise ValidationError("serialized spatial event must be a JSON object")
    payload_raw = raw.get("payload")
    if not isinstance(payload_raw, dict):
        raise ValidationError("serialized spatial event payload must be an object")
    sequence = raw.get("sequence")
    event_type = raw.get("event_type")
    entity_id = raw.get("entity_id")
    schema_version = raw.get("schema_version")
    if not _is_int(sequence):
        raise ValidationError("spatial event sequence must be an integer")
    if not isinstance(event_type, str):
        raise ValidationError("spatial event event_type must be a string")
    if not isinstance(entity_id, str):
        raise ValidationError("spatial event entity_id must be a string")
    if not _is_int(schema_version):
        raise ValidationError("spatial event schema_version must be an integer")
    return SpatialEvent(
        sequence=sequence,
        event_type=event_type,
        entity_id=entity_id,
        payload=tuple(
            (str(key), _event_value(item))
            for key, item in payload_raw.items()
        ),
        schema_version=schema_version,
    )


def serialize_log(events: tuple[SpatialEvent, ...]) -> str:
    return "\n".join(serialize_event(event) for event in events)


def deserialize_log(value: str) -> tuple[SpatialEvent, ...]:
    if not value.strip():
        return ()
    return tuple(deserialize_event(line) for line in value.splitlines() if line.strip())
