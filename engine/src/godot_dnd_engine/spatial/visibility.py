# engine/src/godot_dnd_engine/spatial/visibility.py
"""Headless line-of-sight and cover authority."""

from __future__ import annotations

from .geometry import line_cells
from .model import COVER_RANK, CoverLevel, CoverResult, GridCell, LineOfSightResult, SpatialState


def _ray_height(
    state: SpatialState,
    source: GridCell,
    target: GridCell,
    index: int,
    count: int,
    source_height_feet: float,
    target_height_feet: float,
) -> float:
    source_z = state.space.cell(source).elevation_feet + source_height_feet
    target_z = state.space.cell(target).elevation_feet + target_height_feet
    if count <= 1:
        return source_z
    fraction = index / float(count - 1)
    return source_z + (target_z - source_z) * fraction


def line_of_sight_between_cells(
    state: SpatialState,
    source: GridCell,
    target: GridCell,
    *,
    source_height_feet: float = 5.0,
    target_height_feet: float = 5.0,
    ignore_entity_ids: frozenset[str] = frozenset(),
) -> LineOfSightResult:
    trace = line_cells(state.space, source, target)
    blockers: set[str] = set()
    for index, cell in enumerate(trace[1:-1], start=1):
        ray_height = _ray_height(
            state,
            source,
            target,
            index,
            len(trace),
            source_height_feet,
            target_height_feet,
        )
        terrain = state.space.cell(cell)
        if terrain.blocks_los:
            terrain_top = terrain.elevation_feet + terrain.obstacle_height_feet
            if ray_height <= terrain_top:
                blockers.add(f"terrain:{cell.x},{cell.y}")
        for placement in state.occupants(cell):
            if placement.entity_id in ignore_entity_ids or not placement.blocks_los:
                continue
            base = state.space.cell(cell).elevation_feet
            if ray_height <= base + placement.height_feet:
                blockers.add(placement.entity_id)
    return LineOfSightResult(
        visible=not blockers,
        cells=trace,
        blockers=tuple(sorted(blockers)),
    )


def line_of_sight_between_entities(
    state: SpatialState,
    source_entity_id: str,
    target_entity_id: str,
    *,
    source_eye_height_feet: float | None = None,
    target_eye_height_feet: float | None = None,
) -> LineOfSightResult:
    source = state.placement(source_entity_id)
    target = state.placement(target_entity_id)
    source_height = (
        max(1.0, source.height_feet * 0.75)
        if source_eye_height_feet is None
        else source_eye_height_feet
    )
    target_height = (
        max(1.0, target.height_feet * 0.75)
        if target_eye_height_feet is None
        else target_eye_height_feet
    )
    best: LineOfSightResult | None = None
    for source_cell in source.occupied_cells():
        for target_cell in target.occupied_cells():
            result = line_of_sight_between_cells(
                state,
                source_cell,
                target_cell,
                source_height_feet=source_height,
                target_height_feet=target_height,
                ignore_entity_ids=frozenset({source_entity_id, target_entity_id}),
            )
            if result.visible:
                return result
            if best is None or len(result.blockers) < len(best.blockers):
                best = result
    if best is None:
        raise AssertionError("spatial placements must occupy at least one cell")
    return best


def cover_between_entities(
    state: SpatialState,
    source_entity_id: str,
    target_entity_id: str,
) -> CoverResult:
    los = line_of_sight_between_entities(state, source_entity_id, target_entity_id)
    if not los.visible:
        return CoverResult(CoverLevel.TOTAL, los.blockers)

    target = state.placement(target_entity_id)
    target_cells = set(target.occupied_cells())
    best_level = CoverLevel.NONE
    best_sources: set[str] = set()
    for cell in los.cells[1:-1]:
        if cell in target_cells:
            continue
        terrain = state.space.cell(cell)
        if COVER_RANK[terrain.cover] > COVER_RANK[best_level]:
            best_level = terrain.cover
            best_sources = {f"terrain:{cell.x},{cell.y}"} if terrain.cover is not CoverLevel.NONE else set()
        elif terrain.cover is best_level and terrain.cover is not CoverLevel.NONE:
            best_sources.add(f"terrain:{cell.x},{cell.y}")
        for placement in state.occupants(cell):
            if placement.entity_id in {source_entity_id, target_entity_id}:
                continue
            if COVER_RANK[placement.cover] > COVER_RANK[best_level]:
                best_level = placement.cover
                best_sources = {placement.entity_id}
            elif placement.cover is best_level and placement.cover is not CoverLevel.NONE:
                best_sources.add(placement.entity_id)
    return CoverResult(best_level, tuple(sorted(best_sources)))
