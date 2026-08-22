# tests/test_ids.py
from __future__ import annotations

import pytest

from godot_dnd_engine.errors import ValidationError
from godot_dnd_engine.ids import StableID, require_id


def test_stable_id_accepts_known_namespace() -> None:
    assert str(StableID("actor:hero-1")) == "actor:hero-1"
    assert require_id("campaign:test", "campaign") == "campaign:test"


@pytest.mark.parametrize(
    "value",
    ["", "hero-1", "unknown:value", "Actor:value", "actor:", "actor:bad value"],
)
def test_stable_id_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValidationError):
        StableID(value)


def test_require_id_rejects_wrong_namespace() -> None:
    with pytest.raises(ValidationError):
        require_id("actor:hero", "campaign")
