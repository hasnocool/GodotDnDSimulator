# engine/src/godot_dnd_engine/serialization.py
"""Strict versioned JSON serialization for snapshots and events."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .errors import ValidationError
from .models import EventEnvelope, GameState

SNAPSHOT_SCHEMA_VERSION = 1
EVENT_SCHEMA_VERSION = 1


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{label} must be a JSON object")
    return value


def state_to_dict(state: GameState) -> dict[str, object]:
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "campaign_id": state.campaign_id,
        "session_id": state.session_id,
        "sequence": state.sequence,
        "tick": state.tick,
        "counters": dict(state.counters),
    }


def state_from_dict(data: Mapping[str, Any]) -> GameState:
    data = _require_mapping(data, "snapshot")
    required = {"schema_version", "campaign_id", "session_id", "sequence", "tick", "counters"}
    if set(data) != required:
        raise ValidationError("snapshot fields do not match schema v1")
    if data["schema_version"] != SNAPSHOT_SCHEMA_VERSION:
        raise ValidationError(f"unsupported snapshot schema version: {data['schema_version']!r}")
    counters = _require_mapping(data["counters"], "snapshot counters")
    normalized_counters: list[tuple[str, int]] = []
    for name, value in counters.items():
        if not isinstance(name, str):
            raise ValidationError("snapshot counter names must be strings")
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError("snapshot counter values must be integers")
        normalized_counters.append((name, value))
    try:
        return GameState(
            campaign_id=data["campaign_id"],
            session_id=data["session_id"],
            sequence=data["sequence"],
            tick=data["tick"],
            counters=tuple(normalized_counters),
        )
    except TypeError as exc:
        raise ValidationError("snapshot contains invalid field types") from exc


def event_to_dict(event: EventEnvelope) -> dict[str, object]:
    return {
        "schema_version": EVENT_SCHEMA_VERSION,
        "event_id": event.event_id,
        "campaign_id": event.campaign_id,
        "session_id": event.session_id,
        "sequence": event.sequence,
        "event_type": event.event_type,
        "version": event.version,
        "tick": event.tick,
        "correlation_id": event.correlation_id,
        "causation_id": event.causation_id,
        "payload": dict(event.payload),
    }


def event_from_dict(data: Mapping[str, Any]) -> EventEnvelope:
    data = _require_mapping(data, "event")
    required = {
        "schema_version",
        "event_id",
        "campaign_id",
        "session_id",
        "sequence",
        "event_type",
        "version",
        "tick",
        "correlation_id",
        "causation_id",
        "payload",
    }
    if set(data) != required:
        raise ValidationError("event fields do not match schema v1")
    if data["schema_version"] != EVENT_SCHEMA_VERSION:
        raise ValidationError(f"unsupported event schema version: {data['schema_version']!r}")
    payload = _require_mapping(data["payload"], "event payload")
    try:
        return EventEnvelope(
            event_id=data["event_id"],
            campaign_id=data["campaign_id"],
            session_id=data["session_id"],
            sequence=data["sequence"],
            event_type=data["event_type"],
            version=data["version"],
            tick=data["tick"],
            correlation_id=data["correlation_id"],
            causation_id=data["causation_id"],
            payload=dict(payload),
        )
    except TypeError as exc:
        raise ValidationError("event contains invalid field types") from exc


def dumps_canonical(value: Mapping[str, object]) -> str:
    """Serialize deterministically for fixtures, hashing, and audit logs."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
