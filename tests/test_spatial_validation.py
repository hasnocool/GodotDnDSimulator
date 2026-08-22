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
from godot_dnd_engine.errors import UnsupportedCommandError, ValidationError
from godot_dnd_engine.rules import Ability, AbilityScore
from godot_dnd_engine.spatial import (
    ConeShape,
    GridCell,
    GridOffset,
    MovementPolicy,
    NavigationPathProposal,
    SpatialEvent,
    SpatialPlacement,
    SpatialQueryService,
    SpatialRuntime,
    SpatialState,
    SquareGridSpace,
    TerrainCell,
    ThreatDefinition,
    apply_spatial_event,
    deserialize_event,
    find_actor_path,
    validate_navigation_proposal,
)


def actor(actor_id: str) -> ActorState:
    return ActorState(
        actor_id=actor_id,
        name=actor_id,
        kind=ActorKind.HERO,
        size=SizeCategory.MEDIUM,
        proficiency_bonus=2,
        abilities=tuple(AbilityScore(ability, 12) for ability in Ability),
        hit_points=HitPoints(10, 10),
        defense=DefenseState(12),
        movement=(MovementSpeed(MovementMode.WALK, 30),),
    )


def test_grid_and_terrain_reject_malformed_values() -> None:
    with pytest.raises(ValidationError):
        GridCell(True, 0)
    with pytest.raises(ValidationError):
        SquareGridSpace("space:test", 0, 2)
    with pytest.raises(ValidationError):
        SquareGridSpace(
            "space:test",
            2,
            2,
            terrain=(TerrainCell(GridCell(3, 0)),),
        )
    with pytest.raises(ValidationError):
        SquareGridSpace(
            "space:test",
            2,
            2,
            terrain=(TerrainCell(GridCell(1, 1)), TerrainCell(GridCell(1, 1))),
        )
    with pytest.raises(ValidationError):
        TerrainCell(GridCell(0, 0), obstacle_height_feet=-1)


def test_placements_reject_invalid_footprints_and_blocking_overlap() -> None:
    with pytest.raises(ValidationError):
        SpatialPlacement("actor:a", GridCell(0, 0), footprint=())
    with pytest.raises(ValidationError):
        SpatialPlacement(
            "actor:a",
            GridCell(0, 0),
            footprint=(GridOffset(1, 0),),
        )
    with pytest.raises(ValidationError):
        SpatialState(
            SquareGridSpace("space:test", 3, 3),
            (
                SpatialPlacement("actor:a", GridCell(1, 1)),
                SpatialPlacement("actor:b", GridCell(1, 1)),
            ),
        )


def test_walk_elevation_policy_and_missing_actor_mode_fail_closed() -> None:
    state = SpatialState(
        SquareGridSpace(
            "space:elevation",
            2,
            1,
            terrain=(TerrainCell(GridCell(1, 0), elevation_feet=10),),
        ),
        (SpatialPlacement("actor:a", GridCell(0, 0)),),
    )
    result = find_actor_path(state, actor("actor:a"), GridCell(1, 0), MovementMode.WALK)
    assert not result.legal
    assert "no legal path" in result.reason

    fly = find_actor_path(state, actor("actor:a"), GridCell(1, 0), MovementMode.FLY)
    assert not fly.legal
    assert "does not support" in fly.reason

    permissive = SpatialRuntime(MovementPolicy(max_walk_step_feet=10))
    moved = permissive.move_entity(
        state,
        actor("actor:a"),
        GridCell(1, 0),
        MovementMode.WALK,
    )
    assert moved.state.placement("actor:a").anchor == GridCell(1, 0)


def test_navigation_proposal_rejects_stale_space_anchor_and_unknown_entity() -> None:
    state = SpatialState(
        SquareGridSpace("space:test", 3, 3),
        (SpatialPlacement("actor:a", GridCell(0, 0)),),
    )
    wrong_space = NavigationPathProposal(
        "godot",
        "space:other",
        "actor:a",
        MovementMode.WALK,
        (GridCell(0, 0), GridCell(1, 0)),
    )
    assert not validate_navigation_proposal(state, wrong_space).legal

    stale = NavigationPathProposal(
        "godot",
        "space:test",
        "actor:a",
        MovementMode.WALK,
        (GridCell(1, 0), GridCell(2, 0)),
    )
    assert not validate_navigation_proposal(state, stale).legal

    unknown = NavigationPathProposal(
        "godot",
        "space:test",
        "actor:missing",
        MovementMode.WALK,
        (GridCell(0, 0), GridCell(1, 0)),
    )
    assert not validate_navigation_proposal(state, unknown).legal


def test_spatial_event_reducer_rejects_sequence_path_and_cost_corruption() -> None:
    state = SpatialState(
        SquareGridSpace("space:test", 4, 2),
        (SpatialPlacement("actor:a", GridCell(0, 0)),),
    )
    valid_payload = (
        ("cost_feet", 5),
        ("from_anchor", (0, 0)),
        ("movement_mode", "walk"),
        ("path", ((0, 0), (1, 0))),
        ("threat_entries", ()),
        ("threat_exits", ()),
        ("to_anchor", (1, 0)),
    )
    with pytest.raises(ValidationError):
        apply_spatial_event(
            state,
            SpatialEvent(2, "entity.moved", "actor:a", valid_payload),
        )
    with pytest.raises(ValidationError):
        apply_spatial_event(
            state,
            SpatialEvent(
                1,
                "entity.moved",
                "actor:a",
                tuple(
                    (key, 10 if key == "cost_feet" else value)
                    for key, value in valid_payload
                ),
            ),
        )
    with pytest.raises(ValidationError):
        apply_spatial_event(
            state,
            SpatialEvent(
                1,
                "entity.moved",
                "actor:a",
                tuple(
                    (key, ((0, 0), (3, 0)) if key == "path" else value)
                    for key, value in valid_payload
                ),
            ),
        )


def test_spatial_event_json_rejects_malformed_payloads() -> None:
    with pytest.raises(ValidationError):
        deserialize_event("[]")
    with pytest.raises(ValidationError):
        deserialize_event(
            '{"entity_id":"actor:a","event_type":"entity.moved","payload":[],"schema_version":1,"sequence":1}'
        )
    with pytest.raises(ValidationError):
        deserialize_event(
            '{"entity_id":"actor:a","event_type":"entity.moved","payload":{"path":[{"x":0}]},"schema_version":1,"sequence":1}'
        )


def test_query_service_rejects_unknown_queries_and_malformed_shapes() -> None:
    state = SpatialState(
        SquareGridSpace("space:test", 3, 3),
        (SpatialPlacement("actor:a", GridCell(0, 0)),),
    )
    service = SpatialQueryService(state, (actor("actor:a"),))
    with pytest.raises(UnsupportedCommandError):
        service.execute("spatial.not-real", {})
    with pytest.raises(ValidationError):
        service.execute("spatial.occupancy", {"cell": {"x": "0", "y": 0}})
    with pytest.raises(ValidationError):
        service.execute(
            "spatial.area",
            {
                "shape": {
                    "kind": "cone",
                    "origin": {"x": 0, "y": 0},
                    "direction": {"x": 0, "y": 0},
                    "length_feet": 10,
                }
            },
        )


def test_shape_and_threat_validation_fail_closed() -> None:
    with pytest.raises(ValidationError):
        ConeShape(GridCell(0, 0), 1, 0, -1)
    with pytest.raises(ValidationError):
        ConeShape(GridCell(0, 0), 1, 0, 10, angle_degrees=181)
    with pytest.raises(ValidationError):
        ThreatDefinition("", 5)
    with pytest.raises(ValidationError):
        ThreatDefinition("actor:a", -1)
