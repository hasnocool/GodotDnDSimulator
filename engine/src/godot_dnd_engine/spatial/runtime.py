# engine/src/godot_dnd_engine/spatial/runtime.py
"""Authoritative v0.6 spatial runtime layered beside tactical combat."""

from __future__ import annotations

from dataclasses import dataclass

from ..actors import ActorState, MovementMode
from ..errors import ValidationError
from .events import SpatialEvent
from .model import GridCell, MovementPolicy, PathResult, SpatialState, ThreatTransition
from .movement import find_actor_path, validate_path
from .navigation import NavigationPathProposal, validate_navigation_proposal
from .reducer import apply_spatial_event
from .threats import ThreatDefinition, path_threat_transitions


@dataclass(frozen=True, slots=True)
class SpatialMoveTransition:
    state: SpatialState
    event: SpatialEvent
    path: PathResult
    threat_transitions: tuple[ThreatTransition, ...] = ()


class SpatialRuntime:
    def __init__(self, policy: MovementPolicy = MovementPolicy()) -> None:
        self.policy = policy

    def move_entity(
        self,
        state: SpatialState,
        actor: ActorState,
        destination: GridCell,
        movement_mode: MovementMode,
        *,
        movement_budget_feet: int | None = None,
        threats: tuple[ThreatDefinition, ...] = (),
    ) -> SpatialMoveTransition:
        if actor.actor_id != state.placement(actor.actor_id).entity_id:
            raise ValidationError("actor and spatial placement IDs do not match")
        path = find_actor_path(
            state,
            actor,
            destination,
            movement_mode,
            budget_feet=movement_budget_feet,
            policy=self.policy,
        )
        if not path.legal:
            raise ValidationError(path.reason)
        return self._transition_for_path(
            state,
            actor.actor_id,
            movement_mode,
            path,
            threats,
        )

    def move_from_navigation_proposal(
        self,
        state: SpatialState,
        actor: ActorState,
        proposal: NavigationPathProposal,
        *,
        movement_budget_feet: int | None = None,
        threats: tuple[ThreatDefinition, ...] = (),
    ) -> SpatialMoveTransition:
        if proposal.entity_id != actor.actor_id:
            raise ValidationError("navigation proposal entity does not match actor")
        speed = actor.movement_speed(proposal.movement_mode)
        if speed is None or speed <= 0:
            raise ValidationError(
                f"actor does not support movement mode {proposal.movement_mode.value}"
            )
        effective_budget = speed if movement_budget_feet is None else movement_budget_feet
        path = validate_navigation_proposal(
            state,
            proposal,
            budget_feet=effective_budget,
            policy=self.policy,
        )
        if not path.legal:
            raise ValidationError(path.reason)
        return self._transition_for_path(
            state,
            actor.actor_id,
            proposal.movement_mode,
            path,
            threats,
        )

    def validate_proposed_path(
        self,
        state: SpatialState,
        actor: ActorState,
        path: tuple[GridCell, ...],
        movement_mode: MovementMode,
        *,
        movement_budget_feet: int | None = None,
    ) -> PathResult:
        speed = actor.movement_speed(movement_mode)
        if speed is None or speed <= 0:
            return PathResult(
                False,
                path,
                0,
                f"actor does not support movement mode {movement_mode.value}",
            )
        budget = speed if movement_budget_feet is None else movement_budget_feet
        return validate_path(
            state,
            actor.actor_id,
            path,
            movement_mode,
            budget_feet=budget,
            policy=self.policy,
        )

    def _transition_for_path(
        self,
        state: SpatialState,
        entity_id: str,
        movement_mode: MovementMode,
        path: PathResult,
        threats: tuple[ThreatDefinition, ...],
    ) -> SpatialMoveTransition:
        if not path.legal or not path.path:
            raise ValidationError("cannot create a spatial movement event from an illegal path")
        threat_transitions = path_threat_transitions(
            state,
            entity_id,
            path.path,
            threats,
        ) if threats else ()
        entries = tuple(
            transition.source_entity_id
            for transition in threat_transitions
            if transition.entered
        )
        exits = tuple(
            transition.source_entity_id
            for transition in threat_transitions
            if transition.exited
        )
        event = SpatialEvent(
            sequence=state.sequence + 1,
            event_type="entity.moved",
            entity_id=entity_id,
            payload=(
                ("cost_feet", path.cost_feet),
                ("from_anchor", (path.path[0].x, path.path[0].y)),
                ("movement_mode", movement_mode.value),
                ("path", tuple((cell.x, cell.y) for cell in path.path)),
                ("threat_entries", entries),
                ("threat_exits", exits),
                ("to_anchor", (path.path[-1].x, path.path[-1].y)),
            ),
        )
        next_state = apply_spatial_event(state, event)
        return SpatialMoveTransition(
            state=next_state,
            event=event,
            path=path,
            threat_transitions=threat_transitions,
        )
