# engine/src/godot_dnd_engine/spatial/model.py
"""Immutable logical spatial state for the v0.6 headless authority."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum

from ..actors import MovementMode
from ..errors import ValidationError


class DistanceMetric(StrEnum):
    GRID = "grid"
    MANHATTAN = "manhattan"
    EUCLIDEAN = "euclidean"


class CoverLevel(StrEnum):
    NONE = "none"
    HALF = "half"
    THREE_QUARTERS = "three_quarters"
    TOTAL = "total"


COVER_RANK: dict[CoverLevel, int] = {
    CoverLevel.NONE: 0,
    CoverLevel.HALF: 1,
    CoverLevel.THREE_QUARTERS: 2,
    CoverLevel.TOTAL: 3,
}

ALL_MOVEMENT_MODES: frozenset[MovementMode] = frozenset(MovementMode)


@dataclass(frozen=True, slots=True, order=True)
class GridCell:
    x: int
    y: int

    def __post_init__(self) -> None:
        for label, value in (("x", self.x), ("y", self.y)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError(f"grid {label} must be an integer")

    def offset(self, dx: int, dy: int) -> GridCell:
        return GridCell(self.x + dx, self.y + dy)


@dataclass(frozen=True, slots=True, order=True)
class GridOffset:
    dx: int
    dy: int

    def __post_init__(self) -> None:
        for label, value in (("dx", self.dx), ("dy", self.dy)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError(f"grid offset {label} must be an integer")


@dataclass(frozen=True, slots=True)
class TerrainCell:
    cell: GridCell
    terrain_id: str = "terrain:open"
    elevation_feet: int = 0
    difficult: bool = False
    blocks_movement: bool = False
    blocks_los: bool = False
    obstacle_height_feet: int = 0
    cover: CoverLevel = CoverLevel.NONE
    allowed_modes: frozenset[MovementMode] = ALL_MOVEMENT_MODES

    def __post_init__(self) -> None:
        if not isinstance(self.terrain_id, str) or not self.terrain_id.strip():
            raise ValidationError("terrain_id must be a non-empty string")
        for label, value in (
            ("elevation_feet", self.elevation_feet),
            ("obstacle_height_feet", self.obstacle_height_feet),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValidationError(f"terrain {label} must be an integer >= 0")
        if not isinstance(self.difficult, bool):
            raise ValidationError("terrain difficult must be a boolean")
        if not isinstance(self.blocks_movement, bool):
            raise ValidationError("terrain blocks_movement must be a boolean")
        if not isinstance(self.blocks_los, bool):
            raise ValidationError("terrain blocks_los must be a boolean")
        if not isinstance(self.cover, CoverLevel):
            raise ValidationError("terrain cover must be a CoverLevel")
        if not isinstance(self.allowed_modes, frozenset) or any(
            not isinstance(mode, MovementMode) for mode in self.allowed_modes
        ):
            raise ValidationError("terrain allowed_modes must contain MovementMode values")
        if self.blocks_los and self.obstacle_height_feet == 0:
            object.__setattr__(self, "obstacle_height_feet", 10_000)


@dataclass(frozen=True, slots=True)
class SquareGridSpace:
    space_id: str
    width: int
    height: int
    cell_size_feet: int = 5
    terrain: tuple[TerrainCell, ...] = ()
    _terrain_by_cell: dict[GridCell, TerrainCell] = field(
        init=False, repr=False, compare=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        if not isinstance(self.space_id, str) or not self.space_id.strip():
            raise ValidationError("space_id must be a non-empty string")
        for label, value in (
            ("width", self.width),
            ("height", self.height),
            ("cell_size_feet", self.cell_size_feet),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValidationError(f"space {label} must be an integer >= 1")
        terrain_by_cell: dict[GridCell, TerrainCell] = {}
        for terrain_cell in self.terrain:
            if not self.contains(terrain_cell.cell):
                raise ValidationError("terrain cell is outside spatial bounds")
            if terrain_cell.cell in terrain_by_cell:
                raise ValidationError("terrain cells must be unique")
            terrain_by_cell[terrain_cell.cell] = terrain_cell
        object.__setattr__(
            self,
            "terrain",
            tuple(sorted(self.terrain, key=lambda item: item.cell)),
        )
        object.__setattr__(self, "_terrain_by_cell", terrain_by_cell)

    def contains(self, cell: GridCell) -> bool:
        return 0 <= cell.x < self.width and 0 <= cell.y < self.height

    def cell(self, cell: GridCell) -> TerrainCell:
        if not self.contains(cell):
            raise ValidationError("grid cell is outside spatial bounds")
        existing = self._terrain_by_cell.get(cell)
        if existing is not None:
            return existing
        return TerrainCell(cell=cell)

    def cells(self) -> tuple[GridCell, ...]:
        return tuple(
            GridCell(x, y)
            for y in range(self.height)
            for x in range(self.width)
        )


@dataclass(frozen=True, slots=True)
class SpatialPlacement:
    entity_id: str
    anchor: GridCell
    footprint: tuple[GridOffset, ...] = (GridOffset(0, 0),)
    height_feet: int = 5
    blocks_movement: bool = True
    blocks_los: bool = False
    cover: CoverLevel = CoverLevel.HALF
    tags: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if not isinstance(self.entity_id, str) or not self.entity_id.strip():
            raise ValidationError("spatial entity_id must be a non-empty string")
        if (
            isinstance(self.height_feet, bool)
            or not isinstance(self.height_feet, int)
            or self.height_feet < 0
        ):
            raise ValidationError("spatial height_feet must be an integer >= 0")
        if not self.footprint:
            raise ValidationError("spatial footprint must contain at least one offset")
        if len(self.footprint) != len(set(self.footprint)):
            raise ValidationError("spatial footprint offsets must be unique")
        if GridOffset(0, 0) not in self.footprint:
            raise ValidationError("spatial footprint must contain the anchor offset 0,0")
        if not isinstance(self.cover, CoverLevel):
            raise ValidationError("spatial placement cover must be a CoverLevel")
        if any(not isinstance(tag, str) or not tag.strip() for tag in self.tags):
            raise ValidationError("spatial placement tags must be non-empty strings")
        object.__setattr__(self, "footprint", tuple(sorted(self.footprint)))

    def occupied_cells(self, anchor: GridCell | None = None) -> tuple[GridCell, ...]:
        origin = self.anchor if anchor is None else anchor
        return tuple(origin.offset(offset.dx, offset.dy) for offset in self.footprint)

    def moved(self, anchor: GridCell) -> SpatialPlacement:
        return replace(self, anchor=anchor)


@dataclass(frozen=True, slots=True)
class SpatialState:
    space: SquareGridSpace
    placements: tuple[SpatialPlacement, ...] = ()
    sequence: int = 0

    def __post_init__(self) -> None:
        if (
            isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or self.sequence < 0
        ):
            raise ValidationError("spatial sequence must be an integer >= 0")
        ids = [item.entity_id for item in self.placements]
        if len(ids) != len(set(ids)):
            raise ValidationError("spatial placement entity IDs must be unique")
        occupancy: dict[GridCell, SpatialPlacement] = {}
        for placement in self.placements:
            for cell in placement.occupied_cells():
                if not self.space.contains(cell):
                    raise ValidationError("spatial placement is outside space bounds")
                if self.space.cell(cell).blocks_movement and placement.blocks_movement:
                    raise ValidationError("blocking placement cannot occupy blocked terrain")
                other = occupancy.get(cell)
                if (
                    other is not None
                    and other.blocks_movement
                    and placement.blocks_movement
                ):
                    raise ValidationError("blocking spatial placements cannot overlap")
                if placement.blocks_movement:
                    occupancy[cell] = placement
        object.__setattr__(
            self,
            "placements",
            tuple(sorted(self.placements, key=lambda item: item.entity_id)),
        )

    def placement(self, entity_id: str) -> SpatialPlacement:
        match = next((item for item in self.placements if item.entity_id == entity_id), None)
        if match is None:
            raise ValidationError(f"unknown spatial entity: {entity_id}")
        return match

    def occupants(self, cell: GridCell) -> tuple[SpatialPlacement, ...]:
        return tuple(
            item for item in self.placements if cell in item.occupied_cells()
        )

    def is_occupiable(
        self,
        placement: SpatialPlacement,
        anchor: GridCell,
        *,
        ignore_entity_id: str | None = None,
    ) -> bool:
        for cell in placement.occupied_cells(anchor):
            if not self.space.contains(cell) or self.space.cell(cell).blocks_movement:
                return False
            for occupant in self.occupants(cell):
                if occupant.entity_id == ignore_entity_id:
                    continue
                if occupant.blocks_movement and placement.blocks_movement:
                    return False
        return True

    def with_anchor(self, entity_id: str, anchor: GridCell, *, sequence: int | None = None) -> SpatialState:
        placement = self.placement(entity_id)
        if not self.is_occupiable(placement, anchor, ignore_entity_id=entity_id):
            raise ValidationError("destination is not occupiable")
        updated = tuple(
            placement.moved(anchor) if item.entity_id == entity_id else item
            for item in self.placements
        )
        return SpatialState(
            space=self.space,
            placements=updated,
            sequence=self.sequence if sequence is None else sequence,
        )


@dataclass(frozen=True, slots=True)
class MovementPolicy:
    allow_diagonal: bool = True
    prevent_corner_cutting: bool = True
    difficult_multiplier: int = 2
    max_walk_step_feet: int = 5
    flying_ignores_difficult: bool = True

    def __post_init__(self) -> None:
        if (
            isinstance(self.difficult_multiplier, bool)
            or not isinstance(self.difficult_multiplier, int)
            or self.difficult_multiplier < 1
        ):
            raise ValidationError("difficult_multiplier must be an integer >= 1")
        if (
            isinstance(self.max_walk_step_feet, bool)
            or not isinstance(self.max_walk_step_feet, int)
            or self.max_walk_step_feet < 0
        ):
            raise ValidationError("max_walk_step_feet must be an integer >= 0")


@dataclass(frozen=True, slots=True)
class MovementCapability:
    mode: MovementMode
    speed_feet: int

    def __post_init__(self) -> None:
        if (
            isinstance(self.speed_feet, bool)
            or not isinstance(self.speed_feet, int)
            or self.speed_feet < 0
        ):
            raise ValidationError("movement capability speed must be an integer >= 0")


@dataclass(frozen=True, slots=True)
class PathResult:
    legal: bool
    path: tuple[GridCell, ...]
    cost_feet: int
    reason: str = ""

    def __post_init__(self) -> None:
        if (
            isinstance(self.cost_feet, bool)
            or not isinstance(self.cost_feet, int)
            or self.cost_feet < 0
        ):
            raise ValidationError("path cost_feet must be an integer >= 0")
        if self.legal and not self.path:
            raise ValidationError("a legal path result must contain a path")
        if not self.legal and not self.reason:
            raise ValidationError("an illegal path result must include a reason")


@dataclass(frozen=True, slots=True)
class ReachableCell:
    cell: GridCell
    cost_feet: int

    def __post_init__(self) -> None:
        if (
            isinstance(self.cost_feet, bool)
            or not isinstance(self.cost_feet, int)
            or self.cost_feet < 0
        ):
            raise ValidationError("reachable cell cost must be an integer >= 0")


@dataclass(frozen=True, slots=True)
class LineOfSightResult:
    visible: bool
    cells: tuple[GridCell, ...]
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CoverResult:
    level: CoverLevel
    sources: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AreaResult:
    cells: tuple[GridCell, ...]
    entity_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ThreatTransition:
    source_entity_id: str
    from_cell: GridCell
    to_cell: GridCell
    entered: bool = False
    exited: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.source_entity_id, str) or not self.source_entity_id.strip():
            raise ValidationError("threat source_entity_id must be a non-empty string")
        if self.entered == self.exited:
            raise ValidationError("threat transition must enter or exit exactly once")
