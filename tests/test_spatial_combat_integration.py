from __future__ import annotations

import pytest
from godot_dnd_engine.actors import (
    ActorKind,
    ActorState,
    DefenseState,
    HitPoints,
    MovementMode,
    MovementSpeed,
    SizeCategory,
)
from godot_dnd_engine.combat import CombatRuntime, EncounterState
from godot_dnd_engine.errors import ValidationError
from godot_dnd_engine.rng import DeterministicRNG
from godot_dnd_engine.rules import Ability, AbilityScore
from godot_dnd_engine.spatial import (
    GridCell,
    SpatialPlacement,
    SpatialRuntime,
    SpatialState,
    SquareGridSpace,
    TerrainCell,
)
from godot_dnd_engine.spatial.integration import move_in_encounter


def actor(actor_id: str) -> ActorState:
    return ActorState(
        actor_id=actor_id,
        name=actor_id,
        kind=ActorKind.HERO,
        size=SizeCategory.MEDIUM,
        proficiency_bonus=2,
        abilities=tuple(AbilityScore(ability, 12) for ability in Ability),
        hit_points=HitPoints(12, 12),
        defense=DefenseState(13),
        movement=(MovementSpeed(MovementMode.WALK, 30),),
    )


def started_encounter() -> tuple[CombatRuntime, EncounterState]:
    actors = (actor("actor:a"), actor("actor:b"))
    runtime = CombatRuntime(DeterministicRNG.from_seed(0))
    preparing = runtime.create_encounter("encounter:spatial", actors)
    return runtime, runtime.start_encounter(preparing).state


def test_legal_spatial_move_spends_exact_combat_movement_cost() -> None:
    combat_runtime, encounter = started_encounter()
    current_id = encounter.current_actor_id
    assert current_id is not None
    spatial_state = SpatialState(
        SquareGridSpace("space:combat", 6, 4),
        (
            SpatialPlacement("actor:a", GridCell(0, 0)),
            SpatialPlacement("actor:b", GridCell(5, 3)),
        ),
    )
    before_budget = encounter.combatant(current_id).economy.movement_remaining
    result = move_in_encounter(
        spatial_runtime=SpatialRuntime(),
        combat_runtime=combat_runtime,
        spatial_state=spatial_state,
        encounter_state=encounter,
        actor_id=current_id,
        destination=GridCell(2, 0) if current_id == "actor:a" else GridCell(3, 3),
    )
    assert result.spatial.path.cost_feet == 10
    remaining = result.combat.state.combatant(current_id).economy.movement_remaining
    assert remaining == before_budget - 10
    expected_anchor = GridCell(2, 0) if current_id == "actor:a" else GridCell(3, 3)
    assert result.spatial.state.placement(current_id).anchor == expected_anchor


def test_difficult_terrain_cost_is_the_value_spent_by_combat() -> None:
    combat_runtime, encounter = started_encounter()
    current_id = encounter.current_actor_id
    assert current_id is not None
    other_id = "actor:b" if current_id == "actor:a" else "actor:a"
    start = GridCell(0, 0)
    spatial_state = SpatialState(
        SquareGridSpace(
            "space:difficult-combat",
            4,
            3,
            terrain=(TerrainCell(GridCell(1, 0), difficult=True),),
        ),
        (
            SpatialPlacement(current_id, start),
            SpatialPlacement(other_id, GridCell(3, 2)),
        ),
    )
    before_budget = encounter.combatant(current_id).economy.movement_remaining
    result = move_in_encounter(
        spatial_runtime=SpatialRuntime(),
        combat_runtime=combat_runtime,
        spatial_state=spatial_state,
        encounter_state=encounter,
        actor_id=current_id,
        destination=GridCell(1, 0),
    )
    assert result.spatial.path.cost_feet == 10
    remaining = result.combat.state.combatant(current_id).economy.movement_remaining
    assert remaining == before_budget - 10


def test_illegal_or_over_budget_move_does_not_mutate_either_input_state() -> None:
    combat_runtime, encounter = started_encounter()
    current_id = encounter.current_actor_id
    assert current_id is not None
    other_id = "actor:b" if current_id == "actor:a" else "actor:a"
    spatial_state = SpatialState(
        SquareGridSpace(
            "space:blocked-combat",
            8,
            3,
            terrain=(
                TerrainCell(GridCell(1, 0), blocks_movement=True),
                TerrainCell(GridCell(1, 1), blocks_movement=True),
            ),
        ),
        (
            SpatialPlacement(current_id, GridCell(0, 0)),
            SpatialPlacement(other_id, GridCell(7, 2)),
        ),
    )
    with pytest.raises(ValidationError):
        move_in_encounter(
            spatial_runtime=SpatialRuntime(),
            combat_runtime=combat_runtime,
            spatial_state=spatial_state,
            encounter_state=encounter,
            actor_id=current_id,
            destination=GridCell(7, 0),
        )
    assert spatial_state.sequence == 0
    assert spatial_state.placement(current_id).anchor == GridCell(0, 0)
    assert encounter.combatant(current_id).economy.movement_remaining == 30
