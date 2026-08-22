# engine/src/godot_dnd_engine/spatial/threats.py
"""Geometric threat-zone transitions without deciding reaction outcomes."""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import ValidationError
from .geometry import distance_between_cells
from .model import DistanceMetric, GridCell, SpatialPlacement, SpatialState, ThreatTransition


@dataclass(frozen=True, slots=True)
class ThreatDefinition:
    source_entity_id: str
    reach_feet: int
    affected_entity_ids: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.source_entity_id, str) or not self.source_entity_id.strip():
            raise ValidationError("threat source_entity_id must be a non-empty string")
        if (
            isinstance(self.reach_feet, bool)
            or not isinstance(self.reach_feet, int)
            or self.reach_feet < 0
        ):
            raise ValidationError("threat reach_feet must be an integer >= 0")
        if any(
            not isinstance(entity_id, str) or not entity_id.strip()
            for entity_id in self.affected_entity_ids
        ):
            raise ValidationError("threat affected entity IDs must be non-empty strings")


def _placement_distance_at_anchor(
    state: SpatialState,
    source: SpatialPlacement,
    moving: SpatialPlacement,
    moving_anchor: GridCell,
) -> float:
    return min(
        distance_between_cells(state.space, source_cell, moving_cell, DistanceMetric.GRID)
        for source_cell in source.occupied_cells()
        for moving_cell in moving.occupied_cells(moving_anchor)
    )


def threatened_cells(
    state: SpatialState,
    threat: ThreatDefinition,
) -> tuple[GridCell, ...]:
    source = state.placement(threat.source_entity_id)
    return tuple(
        cell
        for cell in state.space.cells()
        if min(
            distance_between_cells(state.space, source_cell, cell, DistanceMetric.GRID)
            for source_cell in source.occupied_cells()
        )
        <= threat.reach_feet
    )


def path_threat_transitions(
    state: SpatialState,
    moving_entity_id: str,
    path: tuple[GridCell, ...],
    threats: tuple[ThreatDefinition, ...],
) -> tuple[ThreatTransition, ...]:
    moving = state.placement(moving_entity_id)
    if not path:
        raise ValidationError("threat path must not be empty")
    if path[0] != moving.anchor:
        raise ValidationError("threat path must begin at the moving entity anchor")
    result: list[ThreatTransition] = []
    for source_anchor, target_anchor in zip(path, path[1:], strict=False):
        for threat in sorted(threats, key=lambda item: item.source_entity_id):
            if threat.source_entity_id == moving_entity_id:
                continue
            if threat.affected_entity_ids and moving_entity_id not in threat.affected_entity_ids:
                continue
            source = state.placement(threat.source_entity_id)
            before = _placement_distance_at_anchor(
                state, source, moving, source_anchor
            ) <= threat.reach_feet
            after = _placement_distance_at_anchor(
                state, source, moving, target_anchor
            ) <= threat.reach_feet
            if before == after:
                continue
            result.append(
                ThreatTransition(
                    source_entity_id=threat.source_entity_id,
                    from_cell=source_anchor,
                    to_cell=target_anchor,
                    entered=not before and after,
                    exited=before and not after,
                )
            )
    return tuple(result)
