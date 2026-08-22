from __future__ import annotations

from godot_dnd_engine.actors import MovementMode
from godot_dnd_engine.spatial import (
    GridCell,
    SpatialPlacement,
    SpatialState,
    SquareGridSpace,
    find_path,
)


def test_equal_cost_path_ties_are_stable() -> None:
    state = SpatialState(
        SquareGridSpace("space:determinism", 5, 5),
        (SpatialPlacement("actor:a", GridCell(0, 0)),),
    )
    expected = find_path(
        state,
        "actor:a",
        GridCell(4, 3),
        MovementMode.WALK,
    )
    assert expected.legal
    for _ in range(25):
        assert (
            find_path(
                state,
                "actor:a",
                GridCell(4, 3),
                MovementMode.WALK,
            )
            == expected
        )
