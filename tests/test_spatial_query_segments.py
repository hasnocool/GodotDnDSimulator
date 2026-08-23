from __future__ import annotations

from godot_dnd_engine.actors import (
    ActorKind,
    ActorState,
    DefenseState,
    HitPoints,
    MovementMode,
    MovementSpeed,
    SizeCategory,
)
from godot_dnd_engine.rules import Ability, AbilityScore
from godot_dnd_engine.spatial import (
    GridCell,
    MovementPolicy,
    SpatialPlacement,
    SpatialQueryService,
    SpatialState,
    SquareGridSpace,
    TerrainCell,
)


def _actor() -> ActorState:
    return ActorState(
        actor_id="actor:path-segments",
        name="Path Segment Hero",
        kind=ActorKind.HERO,
        size=SizeCategory.MEDIUM,
        proficiency_bonus=2,
        abilities=tuple(AbilityScore(ability, 12) for ability in Ability),
        hit_points=HitPoints(12, 12),
        defense=DefenseState(13),
        movement=(MovementSpeed(MovementMode.WALK, 30),),
    )


def test_spatial_path_query_returns_authoritative_segment_cost_metadata() -> None:
    actor = _actor()
    state = SpatialState(
        SquareGridSpace(
            "space:path-segments",
            width=4,
            height=2,
            terrain=(
                TerrainCell(
                    GridCell(1, 0),
                    terrain_id="terrain:mud",
                    difficult=True,
                ),
                TerrainCell(
                    GridCell(2, 0),
                    terrain_id="terrain:ledge",
                    elevation_feet=5,
                ),
            ),
        ),
        (SpatialPlacement(actor.actor_id, GridCell(0, 0)),),
    )
    service = SpatialQueryService(
        state,
        (actor,),
        MovementPolicy(allow_diagonal=False),
    )

    result = service.execute(
        "spatial.path",
        {
            "entity_id": actor.actor_id,
            "destination": {"x": 2, "y": 0},
            "movement_mode": "walk",
            "budget_feet": 30,
        },
    )

    assert result["legal"] is True
    assert result["cost_feet"] == 15
    assert result["segments"] == [
        {
            "from": {"x": 0, "y": 0},
            "to": {"x": 1, "y": 0},
            "cost_feet": 10,
            "terrain_id": "terrain:mud",
            "difficult": True,
            "elevation_delta_feet": 0,
            "movement_mode": "walk",
        },
        {
            "from": {"x": 1, "y": 0},
            "to": {"x": 2, "y": 0},
            "cost_feet": 5,
            "terrain_id": "terrain:ledge",
            "difficult": False,
            "elevation_delta_feet": 5,
            "movement_mode": "walk",
        },
    ]


def test_illegal_spatial_path_has_no_segment_metadata() -> None:
    actor = _actor()
    state = SpatialState(
        SquareGridSpace(
            "space:path-segments-blocked",
            width=2,
            height=1,
            terrain=(
                TerrainCell(
                    GridCell(1, 0),
                    terrain_id="terrain:wall",
                    blocks_movement=True,
                ),
            ),
        ),
        (SpatialPlacement(actor.actor_id, GridCell(0, 0)),),
    )
    result = SpatialQueryService(state, (actor,)).execute(
        "spatial.path",
        {
            "entity_id": actor.actor_id,
            "destination": {"x": 1, "y": 0},
            "movement_mode": "walk",
            "budget_feet": 30,
        },
    )
    assert result["legal"] is False
    assert result["segments"] == []
