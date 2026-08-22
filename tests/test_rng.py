# tests/test_rng.py
from __future__ import annotations

import pytest

from godot_dnd_engine.errors import ValidationError
from godot_dnd_engine.rng import DeterministicRNG


def test_pcg32_known_vector_is_stable() -> None:
    rng = DeterministicRNG.from_seed(42)
    assert [rng.next_uint32() for _ in range(6)] == [
        2707161783,
        2068313097,
        3122475824,
        2211639955,
        3215226955,
        3421331566,
    ]


def test_same_seed_produces_same_sequence() -> None:
    left = DeterministicRNG.from_seed(987654321)
    right = DeterministicRNG.from_seed(987654321)
    assert [left.roll_die(20) for _ in range(100)] == [right.roll_die(20) for _ in range(100)]


def test_snapshot_restore_continues_exact_sequence() -> None:
    rng = DeterministicRNG.from_seed(1234)
    prefix = [rng.next_uint32() for _ in range(3)]
    restored = DeterministicRNG.restore(rng.snapshot())
    assert prefix
    assert [rng.next_uint32() for _ in range(10)] == [restored.next_uint32() for _ in range(10)]


@pytest.mark.parametrize("bound", [0, -1, (1 << 32) + 1, True, 2.5])
def test_randbelow_rejects_invalid_bounds(bound: object) -> None:
    rng = DeterministicRNG.from_seed(1)
    with pytest.raises(ValidationError):
        rng.randbelow(bound)  # type: ignore[arg-type]


def test_restore_rejects_invalid_state() -> None:
    with pytest.raises(ValidationError):
        DeterministicRNG.restore((1, 2))
