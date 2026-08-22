# engine/src/godot_dnd_engine/engine.py
"""Authoritative command validation, resolution, event emission, and reduction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .dice import DiceExpression, roll_expression
from .errors import SequenceError, UnsupportedCommandError, ValidationError
from .ids import require_id
from .models import CommandEnvelope, EventEnvelope, GameState, SimulationSnapshot
from .reducer import apply_event
from .rng import DeterministicRNG


@dataclass(slots=True)
class SimulationEngine:
    """Minimal deterministic engine proving the v0.1 authority boundary."""

    state: GameState
    rng: DeterministicRNG

    @classmethod
    def create(
        cls,
        *,
        campaign_id: str,
        session_id: str,
        seed: int,
    ) -> SimulationEngine:
        require_id(campaign_id, "campaign")
        require_id(session_id, "session")
        return cls(
            state=GameState(campaign_id=campaign_id, session_id=session_id),
            rng=DeterministicRNG.from_seed(seed),
        )

    @classmethod
    def restore(cls, snapshot: SimulationSnapshot) -> SimulationEngine:
        """Restore state and RNG position so future commands remain deterministic."""

        if snapshot.rng_algorithm != DeterministicRNG.ALGORITHM:
            raise ValidationError(
                f"unsupported RNG algorithm: {snapshot.rng_algorithm!r}; "
                f"expected {DeterministicRNG.ALGORITHM!r}"
            )
        return cls(
            state=snapshot.state,
            rng=DeterministicRNG.restore((snapshot.rng_state, snapshot.rng_increment)),
        )

    def snapshot(self) -> SimulationSnapshot:
        """Capture a complete deterministic continuation point."""

        rng_state, rng_increment = self.rng.snapshot()
        return SimulationSnapshot(
            state=self.state,
            rng_algorithm=self.rng.ALGORITHM,
            rng_state=rng_state,
            rng_increment=rng_increment,
        )

    def handle(self, command: CommandEnvelope) -> tuple[EventEnvelope, ...]:
        """Validate and resolve one command, then atomically reduce emitted events."""

        self._validate_envelope(command)
        if command.command_type == "simulation.roll_dice":
            events = (self._resolve_roll_dice(command),)
        elif command.command_type == "simulation.advance_tick":
            events = (self._resolve_advance_tick(command),)
        else:
            raise UnsupportedCommandError(command.command_type)

        next_state = self.state
        for event in events:
            next_state = apply_event(next_state, event)
        self.state = next_state
        return events

    def _validate_envelope(self, command: CommandEnvelope) -> None:
        if command.campaign_id != self.state.campaign_id:
            raise ValidationError("command campaign does not match engine state")
        if command.session_id != self.state.session_id:
            raise ValidationError("command session does not match engine state")
        if (
            command.expected_sequence is not None
            and command.expected_sequence != self.state.sequence
        ):
            raise SequenceError(
                f"expected state sequence {command.expected_sequence}, "
                f"actual {self.state.sequence}"
            )

    def _resolve_roll_dice(self, command: CommandEnvelope) -> EventEnvelope:
        expression_value = command.payload.get("expression")
        counter = command.payload.get("counter", "last_roll")
        reason = command.payload.get("reason", "simulation roll")
        target_id = command.payload.get("target_id")

        if not isinstance(expression_value, str):
            raise ValidationError("simulation.roll_dice requires string expression")
        if not isinstance(counter, str) or not counter.strip():
            raise ValidationError("simulation.roll_dice counter must be a non-empty string")
        if not isinstance(reason, str) or not reason.strip():
            raise ValidationError("simulation.roll_dice reason must be a non-empty string")
        if target_id is not None:
            if not isinstance(target_id, str):
                raise ValidationError("target_id must be a string when provided")
            require_id(target_id, "actor")

        roll = roll_expression(
            DiceExpression.parse(expression_value),
            self.rng,
            reason=reason,
            actor_id=command.actor_id,
            target_id=target_id,
        )
        payload: dict[str, Any] = roll.to_dict()
        payload["counter"] = counter.strip()
        return self._event(command, event_type="dice.rolled", payload=payload)

    def _resolve_advance_tick(self, command: CommandEnvelope) -> EventEnvelope:
        amount = command.payload.get("amount", 1)
        if isinstance(amount, bool) or not isinstance(amount, int) or amount < 1:
            raise ValidationError("simulation.advance_tick amount must be an integer >= 1")
        return self._event(
            command,
            event_type="simulation.tick_advanced",
            tick=self.state.tick + amount,
            payload={"amount": amount},
        )

    def _event(
        self,
        command: CommandEnvelope,
        *,
        event_type: str,
        payload: dict[str, Any],
        tick: int | None = None,
    ) -> EventEnvelope:
        sequence = self.state.sequence + 1
        return EventEnvelope(
            event_id=f"event:{sequence:016d}",
            campaign_id=self.state.campaign_id,
            session_id=self.state.session_id,
            sequence=sequence,
            event_type=event_type,
            version=1,
            tick=self.state.tick if tick is None else tick,
            correlation_id=command.command_id,
            causation_id=command.command_id,
            payload=payload,
        )
