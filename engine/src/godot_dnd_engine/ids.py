# engine/src/godot_dnd_engine/ids.py
"""Stable identifier primitives and namespace validation."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .errors import ValidationError

_ID_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,31}:[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")

KNOWN_NAMESPACES = frozenset(
    {
        "actor",
        "campaign",
        "command",
        "effect",
        "event",
        "pack",
        "rule",
        "session",
    }
)


@dataclass(frozen=True, slots=True)
class StableID:
    """A namespaced stable identifier used by serialized engine contracts."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not _ID_RE.fullmatch(self.value):
            raise ValidationError(f"invalid stable id: {self.value!r}")
        if self.namespace not in KNOWN_NAMESPACES:
            raise ValidationError(f"unknown stable id namespace: {self.namespace!r}")

    @property
    def namespace(self) -> str:
        return self.value.split(":", 1)[0]

    def require_namespace(self, namespace: str) -> StableID:
        if self.namespace != namespace:
            raise ValidationError(
                f"expected {namespace!r} id, received namespace {self.namespace!r}"
            )
        return self

    def __str__(self) -> str:
        return self.value


def require_id(value: str, namespace: str) -> str:
    """Validate a serialized identifier and return its canonical string value."""

    return str(StableID(value).require_namespace(namespace))
