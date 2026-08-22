# engine/src/godot_dnd_engine/spatial/geometry.py
"""Deterministic geometry helpers for logical tactical space."""

from __future__ import annotations

from math import ceil, sqrt

from ..errors import ValidationError
from .model import DistanceMetric, GridCell, SpatialPlacement, SpatialState, SquareGridSpace


def cell_center(
    space: SquareGridSpace,
    cell: GridCell,
    *,
    height_offset_feet: float = 0.0,
) -> tuple[float, float, float]:
    terrain = space.cell(cell)
    half = space.cell_size_feet / 2.0
    return (
        cell.x * space.cell_size_feet + half,
        cell.y * space.cell_size_feet + half,
        terrain.elevation_feet + height_offset_feet,
    )


def distance_between_cells(
    space: SquareGridSpace,
    source: GridCell,
    target: GridCell,
    metric: DistanceMetric = DistanceMetric.GRID,
) -> float:
    if not space.contains(source) or not space.contains(target):
        raise ValidationError("distance cells must be inside spatial bounds")
    dx = abs(target.x - source.x)
    dy = abs(target.y - source.y)
    dz_feet = abs(space.cell(target).elevation_feet - space.cell(source).elevation_feet)
    cell_size = space.cell_size_feet
    if metric is DistanceMetric.GRID:
        vertical_steps = ceil(dz_feet / cell_size)
        return float(max(dx, dy, vertical_steps) * cell_size)
    if metric is DistanceMetric.MANHATTAN:
        return float((dx + dy) * cell_size + dz_feet)
    if metric is DistanceMetric.EUCLIDEAN:
        return sqrt((dx * cell_size) ** 2 + (dy * cell_size) ** 2 + dz_feet**2)
    raise ValidationError(f"unsupported distance metric: {metric}")


def distance_between_placements(
    state: SpatialState,
    source_entity_id: str,
    target_entity_id: str,
    metric: DistanceMetric = DistanceMetric.GRID,
) -> float:
    source = state.placement(source_entity_id)
    target = state.placement(target_entity_id)
    return min(
        distance_between_cells(state.space, source_cell, target_cell, metric)
        for source_cell in source.occupied_cells()
        for target_cell in target.occupied_cells()
    )


def placement_in_reach(
    state: SpatialState,
    source_entity_id: str,
    target_entity_id: str,
    reach_feet: int,
    metric: DistanceMetric = DistanceMetric.GRID,
) -> bool:
    if isinstance(reach_feet, bool) or not isinstance(reach_feet, int) or reach_feet < 0:
        raise ValidationError("reach_feet must be an integer >= 0")
    return distance_between_placements(state, source_entity_id, target_entity_id, metric) <= reach_feet


def neighboring_cells(
    space: SquareGridSpace,
    cell: GridCell,
    *,
    allow_diagonal: bool = True,
) -> tuple[GridCell, ...]:
    if not space.contains(cell):
        raise ValidationError("neighbor source cell must be inside spatial bounds")
    candidates: list[GridCell] = []
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue
            if not allow_diagonal and dx != 0 and dy != 0:
                continue
            candidate = cell.offset(dx, dy)
            if space.contains(candidate):
                candidates.append(candidate)
    return tuple(sorted(candidates))


def line_cells(space: SquareGridSpace, source: GridCell, target: GridCell) -> tuple[GridCell, ...]:
    """Return a stable supercover-style grid trace from source through target."""

    if not space.contains(source) or not space.contains(target):
        raise ValidationError("line cells must be inside spatial bounds")
    if source == target:
        return (source,)

    dx = target.x - source.x
    dy = target.y - source.y
    nx = abs(dx)
    ny = abs(dy)
    sign_x = 0 if dx == 0 else (1 if dx > 0 else -1)
    sign_y = 0 if dy == 0 else (1 if dy > 0 else -1)
    x = source.x
    y = source.y
    ix = 0
    iy = 0
    result = [source]

    while ix < nx or iy < ny:
        left = (1 + 2 * ix) * ny
        right = (1 + 2 * iy) * nx
        if left == right:
            x += sign_x
            y += sign_y
            ix += 1
            iy += 1
        elif left < right:
            x += sign_x
            ix += 1
        else:
            y += sign_y
            iy += 1
        cell = GridCell(x, y)
        if not space.contains(cell):
            raise ValidationError("line trace escaped spatial bounds")
        if not result or result[-1] != cell:
            result.append(cell)
    return tuple(result)


def translated_placement_cells(
    placement: SpatialPlacement,
    anchor: GridCell,
) -> tuple[GridCell, ...]:
    return placement.occupied_cells(anchor)
