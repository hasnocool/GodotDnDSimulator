# engine/src/godot_dnd_engine/spatial/__init__.py
"""Public API for the deterministic v0.6 spatial authority."""

from .areas import (
    AreaShape,
    ConeShape,
    CubeShape,
    CylinderShape,
    LineShape,
    SphereShape,
    cells_in_shape,
    query_area,
)
from .events import SPATIAL_EVENT_SCHEMA_VERSION, SpatialEvent
from .geometry import (
    cell_center,
    distance_between_cells,
    distance_between_placements,
    line_cells,
    neighboring_cells,
    placement_in_reach,
)
from .model import (
    ALL_MOVEMENT_MODES,
    AreaResult,
    CoverLevel,
    CoverResult,
    DistanceMetric,
    GridCell,
    GridOffset,
    LineOfSightResult,
    MovementCapability,
    MovementPolicy,
    PathResult,
    ReachableCell,
    SpatialPlacement,
    SpatialState,
    SquareGridSpace,
    TerrainCell,
    ThreatTransition,
)
from .movement import (
    find_actor_path,
    find_path,
    movement_capabilities,
    movement_speed,
    reachable_cells,
    step_cost,
    step_is_legal,
    validate_path,
)
from .navigation import (
    NavigationPathProposal,
    NavigationProposalProvider,
    validate_navigation_proposal,
)
from .query import SpatialQueryService
from .reducer import apply_spatial_event
from .replay import replay_spatial
from .runtime import SpatialMoveTransition, SpatialRuntime
from .serialization import (
    deserialize_event,
    deserialize_log,
    event_to_dict,
    serialize_event,
    serialize_log,
)
from .space import LogicalSpace
from .threats import ThreatDefinition, path_threat_transitions, threatened_cells
from .visibility import (
    cover_between_entities,
    line_of_sight_between_cells,
    line_of_sight_between_entities,
)

__all__ = [
    "ALL_MOVEMENT_MODES",
    "SPATIAL_EVENT_SCHEMA_VERSION",
    "AreaResult",
    "AreaShape",
    "ConeShape",
    "CoverLevel",
    "CoverResult",
    "CubeShape",
    "CylinderShape",
    "DistanceMetric",
    "GridCell",
    "GridOffset",
    "LineOfSightResult",
    "LineShape",
    "LogicalSpace",
    "MovementCapability",
    "MovementPolicy",
    "NavigationPathProposal",
    "NavigationProposalProvider",
    "PathResult",
    "ReachableCell",
    "SpatialEvent",
    "SpatialMoveTransition",
    "SpatialPlacement",
    "SpatialQueryService",
    "SpatialRuntime",
    "SpatialState",
    "SphereShape",
    "SquareGridSpace",
    "TerrainCell",
    "ThreatDefinition",
    "ThreatTransition",
    "apply_spatial_event",
    "cell_center",
    "cells_in_shape",
    "cover_between_entities",
    "deserialize_event",
    "deserialize_log",
    "distance_between_cells",
    "distance_between_placements",
    "event_to_dict",
    "find_actor_path",
    "find_path",
    "line_cells",
    "line_of_sight_between_cells",
    "line_of_sight_between_entities",
    "movement_capabilities",
    "movement_speed",
    "neighboring_cells",
    "path_threat_transitions",
    "placement_in_reach",
    "query_area",
    "reachable_cells",
    "replay_spatial",
    "serialize_event",
    "serialize_log",
    "step_cost",
    "step_is_legal",
    "threatened_cells",
    "validate_navigation_proposal",
    "validate_path",
]
