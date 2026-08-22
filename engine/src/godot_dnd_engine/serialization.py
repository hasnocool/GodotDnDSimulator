# engine/src/godot_dnd_engine/serialization.py
"""Strict versioned JSON serialization for snapshots, state, and events."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .errors import ValidationError
from .models import EventEnvelope, GameState, SimulationSnapshot

SNAPSHOT_SCHEMA_VERSION = 1
EVENT_SCHEMA_VERSION = 1
STATE_SCHEMA_VERSION = 1


def _require_mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValidationError(f"{label} must be a JSON object")
    return value


def state_to_dict(state: GameState) -> dict[str, object]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "campaign_id": state.campaign_id,
        "session_id": state.session_id,
        "sequence": state.sequence,
        "tick": state.tick,
        "counters": dict(state.counters),
    }


def state_from_dict(data: Mapping[str, Any]) -> GameState:
    data = _require_mapping(data, "state")
    required = {
        "schema_version",
        "campaign_id",
        "session_id",
        "sequence",
        "tick",
        "counters",
    }
    if set(data) != required:
        raise ValidationError("state fields do not match schema v1")
    if data["schema_version"] != STATE_SCHEMA_VERSION:
        raise ValidationError(
            f"unsupported state schema version: {data['schema_version']!r}"
        )
    counters = _require_mapping(data["counters"], "state counters")
    normalized_counters: list[tuple[str, int]] = []
    for name, value in counters.items():
        if not isinstance(name, str):
            raise ValidationError("state counter names must be strings")
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError("state counter values must be integers")
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
        raise ValidationError("state contains invalid field types") from exc


def snapshot_to_dict(snapshot: SimulationSnapshot) -> dict[str, object]:
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "state": state_to_dict(snapshot.state),
        "rng": {
            "algorithm": snapshot.rng_algorithm,
            "state": snapshot.rng_state,
            "increment": snapshot.rng_increment,
        },
    }


def snapshot_from_dict(data: Mapping[str, Any]) -> SimulationSnapshot:
    data = _require_mapping(data, "snapshot")
    if set(data) != {"schema_version", "state", "rng"}:
        raise ValidationError("snapshot fields do not match schema v1")
    if data["schema_version"] != SNAPSHOT_SCHEMA_VERSION:
        raise ValidationError(
            f"unsupported snapshot schema version: {data['schema_version']!r}"
        )
    state_data = _require_mapping(data["state"], "snapshot state")
    rng_data = _require_mapping(data["rng"], "snapshot RNG")
    if set(rng_data) != {"algorithm", "state", "increment"}:
        raise ValidationError("snapshot RNG fields do not match schema v1")
    try:
        return SimulationSnapshot(
            state=state_from_dict(state_data),
            rng_algorithm=rng_data["algorithm"],
            rng_state=rng_data["state"],
            rng_increment=rng_data["increment"],
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
        raise ValidationError(
            f"unsupported event schema version: {data['schema_version']!r}"
        )
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
