# engine/src/godot_dnd_engine/rng.py
"""Versioned deterministic random-number generator used by all rules code."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import ValidationError

_MASK_32 = (1 << 32) - 1
_MASK_64 = (1 << 64) - 1
_MULTIPLIER = 6364136223846793005
_DEFAULT_STREAM = 54


@dataclass(slots=True)
class DeterministicRNG:
    """PCG32 RNG with a stable algorithm identifier and explicit state.

    The engine owns instances of this class. Rules code must receive an RNG instance
    instead of calling global or wall-clock-seeded randomness APIs.
    """

    state: int
    increment: int

    ALGORITHM = "pcg32-v1"

    @classmethod
    def from_seed(cls, seed: int, *, stream: int = _DEFAULT_STREAM) -> DeterministicRNG:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValidationError("seed must be an integer")
        if isinstance(stream, bool) or not isinstance(stream, int):
            raise ValidationError("stream must be an integer")

        rng = cls(state=0, increment=((stream & _MASK_64) << 1 | 1) & _MASK_64)
        rng.next_uint32()
        rng.state = (rng.state + (seed & _MASK_64)) & _MASK_64
        rng.next_uint32()
        return rng

    def next_uint32(self) -> int:
        """Return the next deterministic unsigned 32-bit value."""

        old_state = self.state
        self.state = (old_state * _MULTIPLIER + self.increment) & _MASK_64
        xor_shifted = (((old_state >> 18) ^ old_state) >> 27) & _MASK_32
        rotation = (old_state >> 59) & 31
        return ((xor_shifted >> rotation) | (xor_shifted << ((-rotation) & 31))) & _MASK_32

    def randbelow(self, upper_bound: int) -> int:
        """Return a uniform integer in ``[0, upper_bound)`` using rejection sampling."""

        if isinstance(upper_bound, bool) or not isinstance(upper_bound, int):
            raise ValidationError("upper_bound must be an integer")
        if not 1 <= upper_bound <= 1 << 32:
            raise ValidationError("upper_bound must be between 1 and 2**32 inclusive")

        if upper_bound == 1 << 32:
            return self.next_uint32()

        threshold = ((1 << 32) - upper_bound) % upper_bound
        while True:
            value = self.next_uint32()
            if value >= threshold:
                return value % upper_bound

    def roll_die(self, sides: int) -> int:
        """Roll one die with ``sides`` faces and return a value from 1 through sides."""

        if isinstance(sides, bool) or not isinstance(sides, int) or sides < 2:
            raise ValidationError("die sides must be an integer >= 2")
        return self.randbelow(sides) + 1

    def snapshot(self) -> tuple[int, int]:
        """Return serializable internal state for deterministic continuation."""

        return (self.state, self.increment)

    @classmethod
    def restore(cls, snapshot: tuple[int, int]) -> DeterministicRNG:
        if (
            not isinstance(snapshot, tuple)
            or len(snapshot) != 2
            or any(isinstance(value, bool) or not isinstance(value, int) for value in snapshot)
        ):
            raise ValidationError("RNG snapshot must contain exactly two integers")
        state, increment = snapshot
        if not 0 <= state <= _MASK_64 or not 0 <= increment <= _MASK_64:
            raise ValidationError("RNG snapshot values must be unsigned 64-bit integers")
        if increment % 2 == 0:
            raise ValidationError("RNG increment must be odd")
        return cls(state=state, increment=increment)
