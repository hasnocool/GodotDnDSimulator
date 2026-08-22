# engine/src/godot_dnd_engine/spells/events.py
"""Versioned spell events, canonical serialization, and RNG continuation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..errors import ValidationError
from ..models import RNGCheckpoint
from ..rng import DeterministicRNG

SPELL_EVENT_SCHEMA_VERSION = 1
SpellEventValue = str | int | bool | None | tuple[str, ...] | tuple[int, ...]


@dataclass(frozen=True, slots=True)
class SpellEvent:
    sequence: int
    event_type: str
    caster_id: str
    spell_id: str
    target_ids: tuple[str, ...] = ()
    payload: tuple[tuple[str, SpellEventValue], ...] = ()
    version: int = SPELL_EVENT_SCHEMA_VERSION
    rng_after: RNGCheckpoint | None = None

    def __post_init__(self) -> None:
        if (
            isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 1
        ):
            raise ValidationError("spell event sequence must be an integer >= 1")
        if (
            not self.event_type.strip()
            or not self.caster_id.strip()
            or not self.spell_id.strip()
        ):
            raise ValidationError("spell event type/caster/spell IDs must be non-empty")
        if self.version != SPELL_EVENT_SCHEMA_VERSION:
            raise ValidationError("unsupported spell event version")
        if len(self.target_ids) != len(set(self.target_ids)):
            raise ValidationError("spell event target IDs must be unique")
        keys = [key for key, _ in self.payload]
        if len(keys) != len(set(keys)) or any(not key.strip() for key in keys):
            raise ValidationError("spell event payload keys must be unique non-empty strings")
        if self.rng_after is not None and not isinstance(self.rng_after, RNGCheckpoint):
            raise ValidationError("spell event rng_after must be a RNGCheckpoint or None")
        object.__setattr__(self, "target_ids", tuple(self.target_ids))
        object.__setattr__(self, "payload", tuple(sorted(self.payload)))

    def value(self, key: str, default: SpellEventValue = None) -> SpellEventValue:
        return dict(self.payload).get(key, default)


def spell_event_to_dict(event: SpellEvent) -> dict[str, Any]:
    payload: dict[str, object] = {}
    for key, value in event.payload:
        payload[key] = list(value) if isinstance(value, tuple) else value
    return {
        "version": event.version,
        "sequence": event.sequence,
        "event_type": event.event_type,
        "caster_id": event.caster_id,
        "spell_id": event.spell_id,
        "target_ids": list(event.target_ids),
        "payload": payload,
        "rng_after": _checkpoint_to_dict(event.rng_after),
    }


def spell_event_from_dict(value: dict[str, Any]) -> SpellEvent:
    if not isinstance(value, dict):
        raise ValidationError("spell event must be an object")
    payload = value.get("payload", {})
    target_ids = value.get("target_ids", [])
    if not isinstance(payload, dict) or not isinstance(target_ids, list):
        raise ValidationError("spell event payload/target_ids are malformed")
    try:
        return SpellEvent(
            version=value.get("version", SPELL_EVENT_SCHEMA_VERSION),
            sequence=value["sequence"],
            event_type=value["event_type"],
            caster_id=value["caster_id"],
            spell_id=value["spell_id"],
            target_ids=tuple(target_ids),
            payload=tuple((str(key), _event_value(item)) for key, item in payload.items()),
            rng_after=_checkpoint_from_raw(value.get("rng_after")),
        )
    except (KeyError, TypeError) as exc:
        raise ValidationError("spell event fields are malformed") from exc


def spell_events_jsonl(events: tuple[SpellEvent, ...]) -> str:
    previous = 0
    rows: list[str] = []
    for event in events:
        if event.sequence != previous + 1:
            raise ValidationError("spell event logs require contiguous sequence numbers")
        previous = event.sequence
        rows.append(
            json.dumps(
                spell_event_to_dict(event),
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    return "\n".join(rows) + ("\n" if rows else "")


def rng_from_spell_events(events: tuple[SpellEvent, ...]) -> DeterministicRNG:
    """Restore the exact future RNG position from the latest checkpointed spell event."""

    for event in reversed(events):
        checkpoint = event.rng_after
        if checkpoint is None:
            continue
        if checkpoint.algorithm != DeterministicRNG.ALGORITHM:
            raise ValidationError(
                f"unsupported spell RNG algorithm: {checkpoint.algorithm!r}"
            )
        return DeterministicRNG.restore((checkpoint.state, checkpoint.increment))
    raise ValidationError("spell event log contains no RNG checkpoint")


def _event_value(value: Any) -> SpellEventValue:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, list):
        if all(isinstance(item, str) for item in value):
            return tuple(value)
        if all(isinstance(item, int) and not isinstance(item, bool) for item in value):
            return tuple(value)
    raise ValidationError("spell event payload contains an unsupported value")


def _checkpoint_to_dict(checkpoint: RNGCheckpoint | None) -> dict[str, object] | None:
    if checkpoint is None:
        return None
    return {
        "algorithm": checkpoint.algorithm,
        "state": checkpoint.state,
        "increment": checkpoint.increment,
    }


def _checkpoint_from_raw(value: Any) -> RNGCheckpoint | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValidationError("spell event rng_after must be an object or null")
    try:
        return RNGCheckpoint(
            algorithm=value["algorithm"],
            state=value["state"],
            increment=value["increment"],
        )
    except KeyError as exc:
        raise ValidationError("spell event rng_after is missing a required field") from exc
