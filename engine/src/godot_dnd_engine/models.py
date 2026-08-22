# engine/src/godot_dnd_engine/models.py
"""Immutable command, event, snapshot, and game-state domain contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from .errors import ValidationError
from .ids import require_id

_MAX_UINT64 = (1 << 64) - 1


def _freeze_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValidationError("payload must be a mapping")
    return MappingProxyType(dict(payload))


@dataclass(frozen=True, slots=True)
class CommandEnvelope:
    command_id: str
    campaign_id: str
    session_id: str
    command_type: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    version: int = 1
    actor_id: str | None = None
    expected_sequence: int | None = None

    def __post_init__(self) -> None:
        require_id(self.command_id, "command")
        require_id(self.campaign_id, "campaign")
        require_id(self.session_id, "session")
        if self.actor_id is not None:
            require_id(self.actor_id, "actor")
        if (
            isinstance(self.version, bool)
            or not isinstance(self.version, int)
            or self.version < 1
        ):
            raise ValidationError("command version must be an integer >= 1")
        if not isinstance(self.command_type, str) or not self.command_type.strip():
            raise ValidationError("command_type must be a non-empty string")
        if self.expected_sequence is not None and (
            isinstance(self.expected_sequence, bool)
            or not isinstance(self.expected_sequence, int)
            or self.expected_sequence < 0
        ):
            raise ValidationError("expected_sequence must be None or an integer >= 0")
        object.__setattr__(self, "payload", _freeze_payload(self.payload))


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    event_id: str
    campaign_id: str
    session_id: str
    sequence: int
    event_type: str
    correlation_id: str
    causation_id: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    version: int = 1
    tick: int = 0

    def __post_init__(self) -> None:
        require_id(self.event_id, "event")
        require_id(self.campaign_id, "campaign")
        require_id(self.session_id, "session")
        require_id(self.correlation_id, "command")
        require_id(self.causation_id, "command")
        if (
            isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 1
        ):
            raise ValidationError("event sequence must be an integer >= 1")
        if not isinstance(self.event_type, str) or not self.event_type.strip():
            raise ValidationError("event_type must be a non-empty string")
        if (
            isinstance(self.version, bool)
            or not isinstance(self.version, int)
            or self.version < 1
        ):
            raise ValidationError("event version must be an integer >= 1")
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise ValidationError("event tick must be an integer >= 0")
        object.__setattr__(self, "payload", _freeze_payload(self.payload))


@dataclass(frozen=True, slots=True)
class GameState:
    campaign_id: str
    session_id: str
    sequence: int = 0
    tick: int = 0
    counters: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        require_id(self.campaign_id, "campaign")
        require_id(self.session_id, "session")
        if (
            isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 0
        ):
            raise ValidationError("state sequence must be an integer >= 0")
        if isinstance(self.tick, bool) or not isinstance(self.tick, int) or self.tick < 0:
            raise ValidationError("state tick must be an integer >= 0")
        normalized: list[tuple[str, int]] = []
        seen: set[str] = set()
        for entry in self.counters:
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise ValidationError("counter entries must be (name, integer) tuples")
            name, value = entry
            if not isinstance(name, str) or not name:
                raise ValidationError("counter name must be a non-empty string")
            if name in seen:
                raise ValidationError(f"duplicate counter name: {name!r}")
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError("counter value must be an integer")
            seen.add(name)
            normalized.append((name, value))
        object.__setattr__(self, "counters", tuple(sorted(normalized)))

    def counter(self, name: str, default: int = 0) -> int:
        for key, value in self.counters:
            if key == name:
                return value
        return default

    def with_counter(
        self,
        name: str,
        value: int,
        *,
        sequence: int,
        tick: int,
    ) -> GameState:
        updated = dict(self.counters)
        updated[name] = value
        return GameState(
            campaign_id=self.campaign_id,
            session_id=self.session_id,
            sequence=sequence,
            tick=tick,
            counters=tuple(updated.items()),
        )


@dataclass(frozen=True, slots=True)
class SimulationSnapshot:
    """Complete deterministic continuation point for an engine instance."""

    state: GameState
    rng_algorithm: str
    rng_state: int
    rng_increment: int

    def __post_init__(self) -> None:
        if not isinstance(self.rng_algorithm, str) or not self.rng_algorithm.strip():
            raise ValidationError("snapshot RNG algorithm must be a non-empty string")
        for label, value in (
            ("state", self.rng_state),
            ("increment", self.rng_increment),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= _MAX_UINT64
            ):
                raise ValidationError(
                    f"snapshot RNG {label} must be an unsigned 64-bit integer"
                )
        if self.rng_increment % 2 == 0:
            raise ValidationError("snapshot RNG increment must be odd")
