# engine/src/godot_dnd_engine/spatial/integration.py
"""Narrow v0.5/v0.6 integration without duplicating combat action economy."""

from __future__ import annotations

from dataclasses import dataclass

from ..actors import MovementMode
from ..combat import CombatRuntime, CombatTransition, EncounterState
from .model import GridCell, SpatialState
from .runtime import SpatialMoveTransition, SpatialRuntime
from .threats import ThreatDefinition


@dataclass(frozen=True, slots=True)
class CombatSpatialMoveTransition:
    spatial: SpatialMoveTransition
    combat: CombatTransition


def move_in_encounter(
    *,
    spatial_runtime: SpatialRuntime,
    combat_runtime: CombatRuntime,
    spatial_state: SpatialState,
    encounter_state: EncounterState,
    actor_id: str,
    destination: GridCell,
    movement_mode: MovementMode = MovementMode.WALK,
    threats: tuple[ThreatDefinition, ...] = (),
) -> CombatSpatialMoveTransition:
    combatant = encounter_state.combatant(actor_id)
    spatial = spatial_runtime.move_entity(
        spatial_state,
        combatant.actor,
        destination,
        movement_mode,
        movement_budget_feet=combatant.economy.movement_remaining,
        threats=threats,
    )
    combat = combat_runtime.spend_movement(
        encounter_state,
        actor_id,
        spatial.path.cost_feet,
    )
    return CombatSpatialMoveTransition(spatial=spatial, combat=combat)
