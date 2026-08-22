# engine/src/godot_dnd_engine/spatial/query.py
"""Transport-neutral read-only spatial query surface for clients and tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..actors import ActorState, MovementMode
from ..errors import UnsupportedCommandError, ValidationError
from .areas import (
    ConeShape,
    CubeShape,
    CylinderShape,
    LineShape,
    SphereShape,
    query_area,
)
from .geometry import distance_between_placements, placement_in_reach
from .model import DistanceMetric, GridCell, MovementPolicy, SpatialState
from .movement import find_actor_path, find_path, movement_capabilities, reachable_cells
from .threats import ThreatDefinition, threatened_cells
from .visibility import cover_between_entities, line_of_sight_between_entities


@dataclass(frozen=True, slots=True)
class SpatialQueryService:
    state: SpatialState
    actors: tuple[ActorState, ...] = ()
    policy: MovementPolicy = MovementPolicy()
    _actor_by_id: dict[str, ActorState] = field(
        init=False,
        repr=False,
        compare=False,
        default_factory=dict,
    )

    def __post_init__(self) -> None:
        actor_by_id: dict[str, ActorState] = {}
        for actor in self.actors:
            if actor.actor_id in actor_by_id:
                raise ValidationError("spatial query actors must have unique IDs")
            actor_by_id[actor.actor_id] = actor
        object.__setattr__(self, "_actor_by_id", actor_by_id)

    def execute(self, query_type: str, payload: dict[str, Any]) -> dict[str, object]:
        if not isinstance(query_type, str) or not query_type.strip():
            raise ValidationError("spatial query_type must be a non-empty string")
        if not isinstance(payload, dict):
            raise ValidationError("spatial query payload must be an object")
        match query_type:
            case "spatial.occupancy":
                cell = _cell(payload.get("cell"), "cell")
                return {
                    "cell": _cell_dict(cell),
                    "entity_ids": [item.entity_id for item in self.state.occupants(cell)],
                }
            case "spatial.distance":
                source = _string(payload.get("source_entity_id"), "source_entity_id")
                target = _string(payload.get("target_entity_id"), "target_entity_id")
                metric = _metric(payload.get("metric", DistanceMetric.GRID.value))
                return {
                    "distance_feet": distance_between_placements(
                        self.state, source, target, metric
                    ),
                    "metric": metric.value,
                }
            case "spatial.reach":
                source = _string(payload.get("source_entity_id"), "source_entity_id")
                target = _string(payload.get("target_entity_id"), "target_entity_id")
                reach = _integer(payload.get("reach_feet"), "reach_feet")
                metric = _metric(payload.get("metric", DistanceMetric.GRID.value))
                distance = distance_between_placements(self.state, source, target, metric)
                return {
                    "in_reach": placement_in_reach(
                        self.state, source, target, reach, metric
                    ),
                    "distance_feet": distance,
                    "reach_feet": reach,
                    "metric": metric.value,
                }
            case "spatial.path":
                return self._path(payload)
            case "spatial.reachable":
                return self._reachable(payload)
            case "spatial.los":
                source = _string(payload.get("source_entity_id"), "source_entity_id")
                target = _string(payload.get("target_entity_id"), "target_entity_id")
                result = line_of_sight_between_entities(self.state, source, target)
                return {
                    "visible": result.visible,
                    "cells": [_cell_dict(cell) for cell in result.cells],
                    "blockers": list(result.blockers),
                }
            case "spatial.cover":
                source = _string(payload.get("source_entity_id"), "source_entity_id")
                target = _string(payload.get("target_entity_id"), "target_entity_id")
                result = cover_between_entities(self.state, source, target)
                return {"cover": result.level.value, "sources": list(result.sources)}
            case "spatial.area":
                shape = _shape(payload.get("shape"))
                result = query_area(self.state, shape)
                return {
                    "cells": [_cell_dict(cell) for cell in result.cells],
                    "entity_ids": list(result.entity_ids),
                }
            case "spatial.movement_modes":
                actor = self._actor(_string(payload.get("actor_id"), "actor_id"))
                return {
                    "actor_id": actor.actor_id,
                    "modes": [
                        {"mode": item.mode.value, "speed_feet": item.speed_feet}
                        for item in movement_capabilities(actor)
                    ],
                }
            case "spatial.threatened_cells":
                source = _string(payload.get("source_entity_id"), "source_entity_id")
                reach = _integer(payload.get("reach_feet"), "reach_feet")
                cells = threatened_cells(self.state, ThreatDefinition(source, reach))
                return {"cells": [_cell_dict(cell) for cell in cells]}
            case _:
                raise UnsupportedCommandError(f"unsupported spatial query: {query_type}")

    def _actor(self, actor_id: str) -> ActorState:
        actor = self._actor_by_id.get(actor_id)
        if actor is None:
            raise ValidationError(f"spatial query has no actor state for {actor_id}")
        return actor

    def _path(self, payload: dict[str, Any]) -> dict[str, object]:
        entity_id = _string(payload.get("entity_id"), "entity_id")
        destination = _cell(payload.get("destination"), "destination")
        mode = _mode(payload.get("movement_mode"))
        budget_raw = payload.get("budget_feet")
        budget = None if budget_raw is None else _integer(budget_raw, "budget_feet")
        actor = self._actor_by_id.get(entity_id)
        if actor is None:
            result = find_path(
                self.state,
                entity_id,
                destination,
                mode,
                budget_feet=budget,
                policy=self.policy,
            )
        else:
            result = find_actor_path(
                self.state,
                actor,
                destination,
                mode,
                budget_feet=budget,
                policy=self.policy,
            )
        return {
            "legal": result.legal,
            "path": [_cell_dict(cell) for cell in result.path],
            "cost_feet": result.cost_feet,
            "reason": result.reason,
        }

    def _reachable(self, payload: dict[str, Any]) -> dict[str, object]:
        entity_id = _string(payload.get("entity_id"), "entity_id")
        mode = _mode(payload.get("movement_mode"))
        budget = _integer(payload.get("budget_feet"), "budget_feet")
        actor = self._actor_by_id.get(entity_id)
        if actor is not None:
            speed = actor.movement_speed(mode)
            if speed is None or speed <= 0:
                raise ValidationError(f"actor does not support movement mode {mode.value}")
        cells = reachable_cells(
            self.state,
            entity_id,
            mode,
            budget,
            policy=self.policy,
        )
        return {
            "cells": [
                {"cell": _cell_dict(item.cell), "cost_feet": item.cost_feet}
                for item in cells
            ]
        }


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    return value


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(f"{label} must be an integer >= 0")
    return value


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{label} must be numeric")
    return float(value)


def _cell(value: Any, label: str) -> GridCell:
    if not isinstance(value, dict):
        raise ValidationError(f"{label} must be a cell object")
    x = value.get("x")
    y = value.get("y")
    if (
        isinstance(x, bool)
        or not isinstance(x, int)
        or isinstance(y, bool)
        or not isinstance(y, int)
    ):
        raise ValidationError(f"{label} x/y must be integers")
    return GridCell(x, y)


def _cell_dict(cell: GridCell) -> dict[str, int]:
    return {"x": cell.x, "y": cell.y}


def _mode(value: Any) -> MovementMode:
    if not isinstance(value, str):
        raise ValidationError("movement_mode must be a string")
    try:
        return MovementMode(value)
    except ValueError as exc:
        raise ValidationError("movement_mode is unsupported") from exc


def _metric(value: Any) -> DistanceMetric:
    if not isinstance(value, str):
        raise ValidationError("distance metric must be a string")
    try:
        return DistanceMetric(value)
    except ValueError as exc:
        raise ValidationError("distance metric is unsupported") from exc


def _direction(value: Any) -> tuple[float, float]:
    if not isinstance(value, dict):
        raise ValidationError("shape direction must be an object")
    return (
        _number(value.get("x"), "direction.x"),
        _number(value.get("y"), "direction.y"),
    )


def _shape(value: Any) -> SphereShape | CubeShape | CylinderShape | ConeShape | LineShape:
    if not isinstance(value, dict):
        raise ValidationError("shape must be an object")
    kind = _string(value.get("kind"), "shape.kind")
    if kind == "sphere":
        return SphereShape(
            center=_cell(value.get("center"), "shape.center"),
            radius_feet=_number(value.get("radius_feet"), "shape.radius_feet"),
        )
    if kind == "cube":
        return CubeShape(
            center=_cell(value.get("center"), "shape.center"),
            size_feet=_number(value.get("size_feet"), "shape.size_feet"),
        )
    if kind == "cylinder":
        return CylinderShape(
            center=_cell(value.get("center"), "shape.center"),
            radius_feet=_number(value.get("radius_feet"), "shape.radius_feet"),
            height_feet=_number(value.get("height_feet"), "shape.height_feet"),
        )
    direction = _direction(value.get("direction"))
    if kind == "cone":
        return ConeShape(
            origin=_cell(value.get("origin"), "shape.origin"),
            direction_x=direction[0],
            direction_y=direction[1],
            length_feet=_number(value.get("length_feet"), "shape.length_feet"),
            angle_degrees=_number(value.get("angle_degrees", 90.0), "shape.angle_degrees"),
        )
    if kind == "line":
        return LineShape(
            origin=_cell(value.get("origin"), "shape.origin"),
            direction_x=direction[0],
            direction_y=direction[1],
            length_feet=_number(value.get("length_feet"), "shape.length_feet"),
            width_feet=_number(value.get("width_feet", 5.0), "shape.width_feet"),
        )
    raise ValidationError(f"unsupported area shape kind: {kind}")
