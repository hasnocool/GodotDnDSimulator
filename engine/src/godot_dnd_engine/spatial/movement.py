# engine/src/godot_dnd_engine/spatial/movement.py
"""Authoritative movement legality, cost, pathfinding, and reachability."""

from __future__ import annotations

from heapq import heappop, heappush
from math import ceil

from ..actors import ActorState, MovementMode
from ..errors import ValidationError
from .geometry import distance_between_cells, neighboring_cells
from .model import (
    DistanceMetric,
    GridCell,
    MovementCapability,
    MovementPolicy,
    PathResult,
    ReachableCell,
    SpatialPlacement,
    SpatialState,
)


def movement_capabilities(actor: ActorState) -> tuple[MovementCapability, ...]:
    return tuple(
        MovementCapability(item.mode, item.feet)
        for item in actor.movement
    )


def movement_speed(actor: ActorState, mode: MovementMode) -> int | None:
    return actor.movement_speed(mode)


def _terrain_allows(
    state: SpatialState,
    placement: SpatialPlacement,
    anchor: GridCell,
    mode: MovementMode,
) -> bool:
    if not state.is_occupiable(placement, anchor, ignore_entity_id=placement.entity_id):
        return False
    return all(
        mode in state.space.cell(cell).allowed_modes
        for cell in placement.occupied_cells(anchor)
    )


def _walk_step_is_legal(
    state: SpatialState,
    placement: SpatialPlacement,
    source: GridCell,
    target: GridCell,
    policy: MovementPolicy,
) -> bool:
    for offset in placement.footprint:
        source_cell = source.offset(offset.dx, offset.dy)
        target_cell = target.offset(offset.dx, offset.dy)
        source_height = state.space.cell(source_cell).elevation_feet
        target_height = state.space.cell(target_cell).elevation_feet
        if abs(target_height - source_height) > policy.max_walk_step_feet:
            return False
    return True


def step_is_legal(
    state: SpatialState,
    entity_id: str,
    source: GridCell,
    target: GridCell,
    mode: MovementMode,
    policy: MovementPolicy = MovementPolicy(),
) -> bool:
    placement = state.placement(entity_id)
    if source == target:
        return True
    dx = target.x - source.x
    dy = target.y - source.y
    if abs(dx) > 1 or abs(dy) > 1 or (dx == 0 and dy == 0):
        return False
    if dx != 0 and dy != 0 and not policy.allow_diagonal:
        return False
    if not state.space.contains(target):
        return False
    if not _terrain_allows(state, placement, target, mode):
        return False
    if mode is MovementMode.WALK and not _walk_step_is_legal(
        state, placement, source, target, policy
    ):
        return False
    if dx != 0 and dy != 0 and policy.prevent_corner_cutting:
        horizontal = source.offset(dx, 0)
        vertical = source.offset(0, dy)
        if not _terrain_allows(state, placement, horizontal, mode):
            return False
        if not _terrain_allows(state, placement, vertical, mode):
            return False
        if mode is MovementMode.WALK:
            if not _walk_step_is_legal(state, placement, source, horizontal, policy):
                return False
            if not _walk_step_is_legal(state, placement, source, vertical, policy):
                return False
    return True


def step_cost(
    state: SpatialState,
    entity_id: str,
    source: GridCell,
    target: GridCell,
    mode: MovementMode,
    policy: MovementPolicy = MovementPolicy(),
) -> int:
    if not step_is_legal(state, entity_id, source, target, mode, policy):
        raise ValidationError("spatial movement step is illegal")
    if source == target:
        return 0
    placement = state.placement(entity_id)
    max_vertical_steps = 0
    difficult = False
    for offset in placement.footprint:
        source_cell = source.offset(offset.dx, offset.dy)
        target_cell = target.offset(offset.dx, offset.dy)
        source_height = state.space.cell(source_cell).elevation_feet
        terrain = state.space.cell(target_cell)
        vertical = abs(terrain.elevation_feet - source_height)
        max_vertical_steps = max(
            max_vertical_steps,
            ceil(vertical / state.space.cell_size_feet),
        )
        difficult = difficult or terrain.difficult
    cost = max(1, max_vertical_steps) * state.space.cell_size_feet
    if difficult and not (mode is MovementMode.FLY and policy.flying_ignores_difficult):
        cost *= policy.difficult_multiplier
    return cost


def validate_path(
    state: SpatialState,
    entity_id: str,
    path: tuple[GridCell, ...],
    mode: MovementMode,
    *,
    budget_feet: int | None = None,
    policy: MovementPolicy = MovementPolicy(),
) -> PathResult:
    if budget_feet is not None and (
        isinstance(budget_feet, bool)
        or not isinstance(budget_feet, int)
        or budget_feet < 0
    ):
        raise ValidationError("movement budget must be None or an integer >= 0")
    placement = state.placement(entity_id)
    if not path:
        return PathResult(False, (), 0, "path is empty")
    if path[0] != placement.anchor:
        return PathResult(False, path, 0, "path does not start at the entity anchor")
    total = 0
    for source, target in zip(path, path[1:], strict=False):
        if not step_is_legal(state, entity_id, source, target, mode, policy):
            return PathResult(False, path, total, f"illegal step {source} -> {target}")
        total += step_cost(state, entity_id, source, target, mode, policy)
        if budget_feet is not None and total > budget_feet:
            return PathResult(False, path, total, "path exceeds movement budget")
    return PathResult(True, path, total)


def _heuristic(state: SpatialState, source: GridCell, target: GridCell) -> int:
    return int(distance_between_cells(state.space, source, target, DistanceMetric.GRID))


def find_path(
    state: SpatialState,
    entity_id: str,
    destination: GridCell,
    mode: MovementMode,
    *,
    budget_feet: int | None = None,
    policy: MovementPolicy = MovementPolicy(),
) -> PathResult:
    if budget_feet is not None and (
        isinstance(budget_feet, bool)
        or not isinstance(budget_feet, int)
        or budget_feet < 0
    ):
        raise ValidationError("movement budget must be None or an integer >= 0")
    placement = state.placement(entity_id)
    start = placement.anchor
    if not state.space.contains(destination):
        return PathResult(False, (), 0, "destination is outside spatial bounds")
    if destination == start:
        return PathResult(True, (start,), 0)
    if not _terrain_allows(state, placement, destination, mode):
        return PathResult(False, (), 0, "destination is not occupiable for movement mode")

    frontier: list[tuple[int, int, GridCell]] = []
    heappush(frontier, (_heuristic(state, start, destination), 0, start))
    came_from: dict[GridCell, GridCell | None] = {start: None}
    cost_so_far: dict[GridCell, int] = {start: 0}

    while frontier:
        _, current_cost, current = heappop(frontier)
        if current_cost != cost_so_far.get(current):
            continue
        if current == destination:
            break
        for neighbor in neighboring_cells(
            state.space,
            current,
            allow_diagonal=policy.allow_diagonal,
        ):
            if not step_is_legal(state, entity_id, current, neighbor, mode, policy):
                continue
            new_cost = current_cost + step_cost(
                state, entity_id, current, neighbor, mode, policy
            )
            if budget_feet is not None and new_cost > budget_feet:
                continue
            previous = cost_so_far.get(neighbor)
            if previous is not None and new_cost >= previous:
                continue
            cost_so_far[neighbor] = new_cost
            came_from[neighbor] = current
            priority = new_cost + _heuristic(state, neighbor, destination)
            heappush(frontier, (priority, new_cost, neighbor))

    if destination not in came_from:
        reason = "no legal path"
        if budget_feet is not None:
            reason = "no legal path within movement budget"
        return PathResult(False, (), 0, reason)

    reverse_path = [destination]
    cursor = destination
    while cursor != start:
        previous = came_from[cursor]
        if previous is None:
            raise AssertionError("path reconstruction reached an unexpected root")
        reverse_path.append(previous)
        cursor = previous
    path = tuple(reversed(reverse_path))
    return PathResult(True, path, cost_so_far[destination])


def reachable_cells(
    state: SpatialState,
    entity_id: str,
    mode: MovementMode,
    budget_feet: int,
    *,
    policy: MovementPolicy = MovementPolicy(),
) -> tuple[ReachableCell, ...]:
    if isinstance(budget_feet, bool) or not isinstance(budget_feet, int) or budget_feet < 0:
        raise ValidationError("movement budget must be an integer >= 0")
    start = state.placement(entity_id).anchor
    frontier: list[tuple[int, GridCell]] = [(0, start)]
    costs: dict[GridCell, int] = {start: 0}

    while frontier:
        current_cost, current = heappop(frontier)
        if current_cost != costs.get(current):
            continue
        for neighbor in neighboring_cells(
            state.space,
            current,
            allow_diagonal=policy.allow_diagonal,
        ):
            if not step_is_legal(state, entity_id, current, neighbor, mode, policy):
                continue
            new_cost = current_cost + step_cost(
                state, entity_id, current, neighbor, mode, policy
            )
            if new_cost > budget_feet:
                continue
            previous = costs.get(neighbor)
            if previous is not None and new_cost >= previous:
                continue
            costs[neighbor] = new_cost
            heappush(frontier, (new_cost, neighbor))

    return tuple(
        ReachableCell(cell, cost)
        for cell, cost in sorted(costs.items(), key=lambda item: (item[1], item[0]))
    )


def find_actor_path(
    state: SpatialState,
    actor: ActorState,
    destination: GridCell,
    mode: MovementMode,
    *,
    budget_feet: int | None = None,
    policy: MovementPolicy = MovementPolicy(),
) -> PathResult:
    if actor.actor_id != state.placement(actor.actor_id).entity_id:
        raise ValidationError("actor and spatial placement IDs do not match")
    speed = movement_speed(actor, mode)
    if speed is None or speed <= 0:
        return PathResult(False, (), 0, f"actor does not support movement mode {mode.value}")
    effective_budget = speed if budget_feet is None else budget_feet
    return find_path(
        state,
        actor.actor_id,
        destination,
        mode,
        budget_feet=effective_budget,
        policy=policy,
    )
