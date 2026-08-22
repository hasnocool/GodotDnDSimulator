# engine/src/godot_dnd_engine/spatial/areas.py
"""Generic grid area/shape queries for targeting and effect previews."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, hypot, radians, sqrt

from ..errors import ValidationError
from .geometry import cell_center
from .model import AreaResult, GridCell, SpatialState, SquareGridSpace


def _positive_number(value: float | int, label: str, *, allow_zero: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{label} must be numeric")
    numeric = float(value)
    if numeric < 0 or (not allow_zero and numeric == 0):
        operator = ">= 0" if allow_zero else "> 0"
        raise ValidationError(f"{label} must be {operator}")
    return numeric


def _normalized_direction(dx: float, dy: float) -> tuple[float, float]:
    length = hypot(dx, dy)
    if length == 0:
        raise ValidationError("area direction must be non-zero")
    return dx / length, dy / length


@dataclass(frozen=True, slots=True)
class SphereShape:
    center: GridCell
    radius_feet: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "radius_feet", _positive_number(self.radius_feet, "sphere radius"))

    def contains(self, space: SquareGridSpace, cell: GridCell) -> bool:
        cx, cy, cz = cell_center(space, self.center)
        px, py, pz = cell_center(space, cell)
        return sqrt((px - cx) ** 2 + (py - cy) ** 2 + (pz - cz) ** 2) <= self.radius_feet


@dataclass(frozen=True, slots=True)
class CubeShape:
    center: GridCell
    size_feet: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "size_feet", _positive_number(self.size_feet, "cube size"))

    def contains(self, space: SquareGridSpace, cell: GridCell) -> bool:
        cx, cy, cz = cell_center(space, self.center)
        px, py, pz = cell_center(space, cell)
        half = self.size_feet / 2.0
        return abs(px - cx) <= half and abs(py - cy) <= half and abs(pz - cz) <= half


@dataclass(frozen=True, slots=True)
class CylinderShape:
    center: GridCell
    radius_feet: float
    height_feet: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "radius_feet", _positive_number(self.radius_feet, "cylinder radius"))
        object.__setattr__(self, "height_feet", _positive_number(self.height_feet, "cylinder height"))

    def contains(self, space: SquareGridSpace, cell: GridCell) -> bool:
        cx, cy, cz = cell_center(space, self.center)
        px, py, pz = cell_center(space, cell)
        horizontal = hypot(px - cx, py - cy)
        return horizontal <= self.radius_feet and abs(pz - cz) <= self.height_feet / 2.0


@dataclass(frozen=True, slots=True)
class ConeShape:
    origin: GridCell
    direction_x: float
    direction_y: float
    length_feet: float
    angle_degrees: float = 90.0

    def __post_init__(self) -> None:
        direction = _normalized_direction(float(self.direction_x), float(self.direction_y))
        object.__setattr__(self, "direction_x", direction[0])
        object.__setattr__(self, "direction_y", direction[1])
        object.__setattr__(self, "length_feet", _positive_number(self.length_feet, "cone length"))
        angle = _positive_number(self.angle_degrees, "cone angle")
        if angle > 180:
            raise ValidationError("cone angle must be <= 180 degrees")
        object.__setattr__(self, "angle_degrees", angle)

    def contains(self, space: SquareGridSpace, cell: GridCell) -> bool:
        if cell == self.origin:
            return True
        ox, oy, oz = cell_center(space, self.origin)
        px, py, pz = cell_center(space, cell)
        vx = px - ox
        vy = py - oy
        vz = pz - oz
        distance = sqrt(vx * vx + vy * vy + vz * vz)
        if distance == 0 or distance > self.length_feet:
            return False
        alignment = (vx * self.direction_x + vy * self.direction_y) / distance
        return alignment >= cos(radians(self.angle_degrees / 2.0))


@dataclass(frozen=True, slots=True)
class LineShape:
    origin: GridCell
    direction_x: float
    direction_y: float
    length_feet: float
    width_feet: float = 5.0

    def __post_init__(self) -> None:
        direction = _normalized_direction(float(self.direction_x), float(self.direction_y))
        object.__setattr__(self, "direction_x", direction[0])
        object.__setattr__(self, "direction_y", direction[1])
        object.__setattr__(self, "length_feet", _positive_number(self.length_feet, "line length"))
        object.__setattr__(self, "width_feet", _positive_number(self.width_feet, "line width"))

    def contains(self, space: SquareGridSpace, cell: GridCell) -> bool:
        ox, oy, oz = cell_center(space, self.origin)
        px, py, pz = cell_center(space, cell)
        vx = px - ox
        vy = py - oy
        projection = vx * self.direction_x + vy * self.direction_y
        if projection < 0 or projection > self.length_feet:
            return False
        perpendicular_x = vx - projection * self.direction_x
        perpendicular_y = vy - projection * self.direction_y
        perpendicular = sqrt(perpendicular_x**2 + perpendicular_y**2 + (pz - oz) ** 2)
        return perpendicular <= self.width_feet / 2.0


type AreaShape = SphereShape | CubeShape | CylinderShape | ConeShape | LineShape


def cells_in_shape(state: SpatialState, shape: AreaShape) -> tuple[GridCell, ...]:
    anchor = shape.center if isinstance(shape, (SphereShape, CubeShape, CylinderShape)) else shape.origin
    if not state.space.contains(anchor):
        raise ValidationError("area shape anchor must be inside spatial bounds")
    return tuple(cell for cell in state.space.cells() if shape.contains(state.space, cell))


def query_area(state: SpatialState, shape: AreaShape) -> AreaResult:
    cells = cells_in_shape(state, shape)
    cell_set = set(cells)
    entity_ids = tuple(
        sorted(
            placement.entity_id
            for placement in state.placements
            if any(cell in cell_set for cell in placement.occupied_cells())
        )
    )
    return AreaResult(cells=cells, entity_ids=entity_ids)
