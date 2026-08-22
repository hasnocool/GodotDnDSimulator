# engine/src/godot_dnd_engine/spatial/navigation.py
"""Transport-neutral contract for validating navigation proposals from Godot or other clients."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..actors import MovementMode
from ..errors import ValidationError
from .model import GridCell, MovementPolicy, PathResult, SpatialState
from .movement import validate_path


@dataclass(frozen=True, slots=True)
class NavigationPathProposal:
    adapter_id: str
    space_id: str
    entity_id: str
    movement_mode: MovementMode
    cells: tuple[GridCell, ...]
    observation_revision: int = 0

    def __post_init__(self) -> None:
        for label, value in (
            ("adapter_id", self.adapter_id),
            ("space_id", self.space_id),
            ("entity_id", self.entity_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(f"navigation {label} must be a non-empty string")
        if not isinstance(self.movement_mode, MovementMode):
            raise ValidationError("navigation movement_mode must be a MovementMode")
        if not self.cells:
            raise ValidationError("navigation proposal must contain at least one logical cell")
        if (
            isinstance(self.observation_revision, bool)
            or not isinstance(self.observation_revision, int)
            or self.observation_revision < 0
        ):
            raise ValidationError("navigation observation_revision must be an integer >= 0")


class NavigationProposalProvider(Protocol):
    """Presentation-side adapter contract; implementations may wrap Godot NavigationServer."""

    def propose_path(
        self,
        *,
        space_id: str,
        entity_id: str,
        start: GridCell,
        destination: GridCell,
        movement_mode: MovementMode,
    ) -> NavigationPathProposal: ...


def validate_navigation_proposal(
    state: SpatialState,
    proposal: NavigationPathProposal,
    *,
    budget_feet: int | None = None,
    policy: MovementPolicy = MovementPolicy(),
) -> PathResult:
    if proposal.space_id != state.space.space_id:
        return PathResult(False, proposal.cells, 0, "navigation proposal targets another space")
    try:
        placement = state.placement(proposal.entity_id)
    except ValidationError:
        return PathResult(False, proposal.cells, 0, "navigation proposal references unknown entity")
    if proposal.cells[0] != placement.anchor:
        return PathResult(False, proposal.cells, 0, "navigation proposal starts at stale anchor")
    return validate_path(
        state,
        proposal.entity_id,
        proposal.cells,
        proposal.movement_mode,
        budget_feet=budget_feet,
        policy=policy,
    )
