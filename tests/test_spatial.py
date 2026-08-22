from __future__ import annotations

from math import isclose

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
    ConeShape,
    CoverLevel,
    CubeShape,
    DistanceMetric,
    GridCell,
    GridOffset,
    LineShape,
    MovementPolicy,
    NavigationPathProposal,
    SpatialPlacement,
    SpatialQueryService,
    SpatialRuntime,
    SpatialState,
    SphereShape,
    SquareGridSpace,
    TerrainCell,
    ThreatDefinition,
    cover_between_entities,
    deserialize_event,
    distance_between_placements,
    find_actor_path,
    find_path,
    line_of_sight_between_entities,
    movement_capabilities,
    path_threat_transitions,
    placement_in_reach,
    query_area,
    reachable_cells,
    replay_spatial,
    serialize_event,
    step_cost,
    validate_navigation_proposal,
)


def actor(
    actor_id: str,
    *,
    movement: tuple[MovementSpeed, ...] | None = None,
) -> ActorState:
    return ActorState(
        actor_id=actor_id,
        name=actor_id,
        kind=ActorKind.HERO,
        size=SizeCategory.MEDIUM,
        proficiency_bonus=2,
        abilities=tuple(AbilityScore(ability, 12) for ability in Ability),
        hit_points=HitPoints(12, 12),
        defense=DefenseState(13),
        movement=movement
        or (
            MovementSpeed(MovementMode.WALK, 30),
            MovementSpeed(MovementMode.CLIMB, 15),
            MovementSpeed(MovementMode.FLY, 40),
        ),
    )


def placement(entity_id: str, x: int, y: int, **kwargs: object) -> SpatialPlacement:
    return SpatialPlacement(entity_id, GridCell(x, y), **kwargs)


def test_occupancy_supports_explicit_large_footprints() -> None:
    space = SquareGridSpace("space:test", 6, 6)
    large = SpatialPlacement(
        "actor:large",
        GridCell(1, 1),
        footprint=(
            GridOffset(0, 0),
            GridOffset(1, 0),
            GridOffset(0, 1),
            GridOffset(1, 1),
        ),
    )
    other = placement("actor:other", 4, 4)
    state = SpatialState(space, (large, other))

    assert tuple(cell for cell in large.occupied_cells()) == (
        GridCell(1, 1),
        GridCell(1, 2),
        GridCell(2, 1),
        GridCell(2, 2),
    )
    assert state.occupants(GridCell(2, 2)) == (large,)
    assert not state.is_occupiable(other, GridCell(2, 2), ignore_entity_id="actor:other")
    assert state.is_occupiable(other, GridCell(3, 3), ignore_entity_id="actor:other")


def test_distance_and_reach_are_headless_and_metric_explicit() -> None:
    state = SpatialState(
        SquareGridSpace("space:distance", 8, 8),
        (placement("actor:a", 0, 0), placement("actor:b", 2, 2)),
    )
    assert distance_between_placements(state, "actor:a", "actor:b") == 10.0
    assert distance_between_placements(
        state, "actor:a", "actor:b", DistanceMetric.MANHATTAN
    ) == 20.0
    assert isclose(
        distance_between_placements(
            state, "actor:a", "actor:b", DistanceMetric.EUCLIDEAN
        ),
        14.1421356237,
    )
    assert placement_in_reach(state, "actor:a", "actor:b", 10)
    assert not placement_in_reach(state, "actor:a", "actor:b", 5)


def test_pathfinding_routes_around_collision_without_cutting_corners() -> None:
    space = SquareGridSpace(
        "space:path",
        5,
        4,
        terrain=(TerrainCell(GridCell(1, 0), blocks_movement=True),),
    )
    state = SpatialState(space, (placement("actor:a", 0, 0),))
    result = find_path(state, "actor:a", GridCell(2, 0), MovementMode.WALK)

    assert result.legal
    assert result.path[0] == GridCell(0, 0)
    assert result.path[-1] == GridCell(2, 0)
    assert GridCell(1, 0) not in result.path
    assert result.cost_feet == 20


def test_difficult_terrain_elevation_and_movement_modes_change_cost_and_legality() -> None:
    difficult_space = SquareGridSpace(
        "space:difficult",
        3,
        2,
        terrain=(TerrainCell(GridCell(1, 0), difficult=True),),
    )
    difficult_state = SpatialState(difficult_space, (placement("actor:a", 0, 0),))
    assert step_cost(
        difficult_state,
        "actor:a",
        GridCell(0, 0),
        GridCell(1, 0),
        MovementMode.WALK,
    ) == 10
    assert step_cost(
        difficult_state,
        "actor:a",
        GridCell(0, 0),
        GridCell(1, 0),
        MovementMode.FLY,
    ) == 5

    elevation_space = SquareGridSpace(
        "space:elevation",
        3,
        1,
        terrain=(
            TerrainCell(
                GridCell(1, 0),
                elevation_feet=10,
                allowed_modes=frozenset({MovementMode.WALK, MovementMode.CLIMB}),
            ),
        ),
    )
    elevation_state = SpatialState(elevation_space, (placement("actor:a", 0, 0),))
    walking = find_path(elevation_state, "actor:a", GridCell(1, 0), MovementMode.WALK)
    climbing = find_path(elevation_state, "actor:a", GridCell(1, 0), MovementMode.CLIMB)
    assert not walking.legal
    assert climbing.legal
    assert climbing.cost_feet == 10


def test_actor_movement_adapter_and_reachable_cells_use_explicit_budget() -> None:
    hero = actor("actor:a")
    state = SpatialState(
        SquareGridSpace(
            "space:reachable",
            4,
            3,
            terrain=(TerrainCell(GridCell(1, 0), difficult=True),),
        ),
        (placement("actor:a", 0, 0),),
    )
    capabilities = movement_capabilities(hero)
    assert [(item.mode, item.speed_feet) for item in capabilities] == [
        (MovementMode.CLIMB, 15),
        (MovementMode.FLY, 40),
        (MovementMode.WALK, 30),
    ]
    path = find_actor_path(state, hero, GridCell(3, 0), MovementMode.WALK, budget_feet=15)
    assert not path.legal
    reachable = reachable_cells(state, "actor:a", MovementMode.WALK, 10)
    costs = {item.cell: item.cost_feet for item in reachable}
    assert costs[GridCell(0, 0)] == 0
    assert costs[GridCell(1, 0)] == 10
    assert GridCell(2, 0) not in costs


def test_line_of_sight_and_cover_use_logical_obstacles() -> None:
    blocked = SquareGridSpace(
        "space:los-blocked",
        5,
        3,
        terrain=(TerrainCell(GridCell(2, 1), blocks_los=True),),
    )
    blocked_state = SpatialState(
        blocked,
        (placement("actor:a", 0, 1), placement("actor:b", 4, 1)),
    )
    los = line_of_sight_between_entities(blocked_state, "actor:a", "actor:b")
    assert not los.visible
    assert los.blockers == ("terrain:2,1",)
    assert cover_between_entities(blocked_state, "actor:a", "actor:b").level is CoverLevel.TOTAL

    covered = SquareGridSpace(
        "space:cover",
        5,
        3,
        terrain=(TerrainCell(GridCell(2, 1), cover=CoverLevel.THREE_QUARTERS),),
    )
    covered_state = SpatialState(
        covered,
        (placement("actor:a", 0, 1), placement("actor:b", 4, 1)),
    )
    assert line_of_sight_between_entities(covered_state, "actor:a", "actor:b").visible
    cover = cover_between_entities(covered_state, "actor:a", "actor:b")
    assert cover.level is CoverLevel.THREE_QUARTERS
    assert cover.sources == ("terrain:2,1",)


def test_elevation_can_clear_a_low_los_obstacle() -> None:
    space = SquareGridSpace(
        "space:elevated-los",
        5,
        1,
        terrain=(
            TerrainCell(GridCell(0, 0), elevation_feet=10),
            TerrainCell(
                GridCell(2, 0),
                blocks_los=True,
                obstacle_height_feet=5,
            ),
            TerrainCell(GridCell(4, 0), elevation_feet=10),
        ),
    )
    state = SpatialState(
        space,
        (placement("actor:a", 0, 0), placement("actor:b", 4, 0)),
    )
    assert line_of_sight_between_entities(state, "actor:a", "actor:b").visible


def test_generic_area_shapes_report_cells_and_entities() -> None:
    state = SpatialState(
        SquareGridSpace("space:areas", 7, 7),
        (
            placement("actor:center", 3, 3),
            placement("actor:east", 4, 3),
            placement("actor:far", 6, 6),
        ),
    )
    sphere = query_area(state, SphereShape(GridCell(3, 3), 5))
    assert set(sphere.cells) == {
        GridCell(3, 3),
        GridCell(2, 3),
        GridCell(4, 3),
        GridCell(3, 2),
        GridCell(3, 4),
    }
    assert sphere.entity_ids == ("actor:center", "actor:east")

    cube = query_area(state, CubeShape(GridCell(3, 3), 10))
    assert len(cube.cells) == 9

    cone = query_area(
        state,
        ConeShape(GridCell(3, 3), direction_x=1, direction_y=0, length_feet=15),
    )
    assert GridCell(4, 3) in cone.cells
    assert GridCell(2, 3) not in cone.cells

    line = query_area(
        state,
        LineShape(GridCell(3, 3), direction_x=1, direction_y=0, length_feet=15),
    )
    assert GridCell(4, 3) in line.cells
    assert GridCell(3, 4) not in line.cells


def test_threat_transitions_are_geometric_inputs_not_reaction_resolution() -> None:
    state = SpatialState(
        SquareGridSpace("space:threat", 7, 5),
        (placement("actor:threat", 2, 2), placement("actor:mover", 3, 2)),
    )
    transitions = path_threat_transitions(
        state,
        "actor:mover",
        (GridCell(3, 2), GridCell(4, 2), GridCell(5, 2)),
        (ThreatDefinition("actor:threat", 5, frozenset({"actor:mover"})),),
    )
    assert len(transitions) == 1
    assert transitions[0].source_entity_id == "actor:threat"
    assert transitions[0].exited
    assert not transitions[0].entered


def test_navigation_proposal_is_only_a_candidate_until_authority_validates_it() -> None:
    state = SpatialState(
        SquareGridSpace(
            "space:navigation",
            4,
            3,
            terrain=(TerrainCell(GridCell(1, 0), blocks_movement=True),),
        ),
        (placement("actor:a", 0, 0),),
    )
    illegal = NavigationPathProposal(
        "godot-nav",
        "space:navigation",
        "actor:a",
        MovementMode.WALK,
        (GridCell(0, 0), GridCell(1, 0), GridCell(2, 0)),
    )
    assert not validate_navigation_proposal(state, illegal).legal

    legal = NavigationPathProposal(
        "godot-nav",
        "space:navigation",
        "actor:a",
        MovementMode.WALK,
        (GridCell(0, 0), GridCell(0, 1), GridCell(1, 1), GridCell(2, 1), GridCell(2, 0)),
    )
    result = validate_navigation_proposal(state, legal)
    assert result.legal
    assert result.cost_feet == 20


def test_spatial_move_event_round_trips_and_replays_to_same_state() -> None:
    hero = actor("actor:a")
    initial = SpatialState(
        SquareGridSpace("space:replay", 5, 3),
        (placement("actor:a", 0, 0),),
    )
    runtime = SpatialRuntime()
    transition = runtime.move_entity(
        initial,
        hero,
        GridCell(2, 0),
        MovementMode.WALK,
        movement_budget_feet=30,
    )
    assert transition.state.sequence == 1
    assert transition.state.placement("actor:a").anchor == GridCell(2, 0)
    assert transition.path.cost_feet == 10

    encoded = serialize_event(transition.event)
    decoded = deserialize_event(encoded)
    assert decoded == transition.event
    assert replay_spatial(initial, (decoded,)) == transition.state


def test_query_service_exposes_bridge_ready_read_only_results() -> None:
    hero = actor("actor:a")
    state = SpatialState(
        SquareGridSpace(
            "space:query",
            6,
            4,
            terrain=(TerrainCell(GridCell(2, 1), cover=CoverLevel.HALF),),
        ),
        (placement("actor:a", 0, 1), placement("actor:b", 4, 1)),
    )
    service = SpatialQueryService(state, (hero,))

    occupancy = service.execute("spatial.occupancy", {"cell": {"x": 0, "y": 1}})
    assert occupancy["entity_ids"] == ["actor:a"]
    reach = service.execute(
        "spatial.reach",
        {
            "source_entity_id": "actor:a",
            "target_entity_id": "actor:b",
            "reach_feet": 20,
        },
    )
    assert reach["in_reach"] is True
    path = service.execute(
        "spatial.path",
        {
            "entity_id": "actor:a",
            "destination": {"x": 2, "y": 1},
            "movement_mode": "walk",
            "budget_feet": 30,
        },
    )
    assert path["legal"] is True
    assert path["cost_feet"] == 10
    modes = service.execute("spatial.movement_modes", {"actor_id": "actor:a"})
    assert {item["mode"] for item in modes["modes"]} == {"walk", "climb", "fly"}
    cover = service.execute(
        "spatial.cover",
        {"source_entity_id": "actor:a", "target_entity_id": "actor:b"},
    )
    assert cover["cover"] == "half"


def test_custom_movement_policy_can_disable_diagonals() -> None:
    state = SpatialState(
        SquareGridSpace("space:policy", 3, 3),
        (placement("actor:a", 0, 0),),
    )
    result = find_path(
        state,
        "actor:a",
        GridCell(1, 1),
        MovementMode.WALK,
        policy=MovementPolicy(allow_diagonal=False),
    )
    assert result.legal
    assert result.cost_feet == 10
    assert len(result.path) == 3
