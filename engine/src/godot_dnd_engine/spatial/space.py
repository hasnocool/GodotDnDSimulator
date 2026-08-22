# engine/src/godot_dnd_engine/spatial/space.py
"""Logical-space protocol kept independent from any rendering/navigation backend."""

from __future__ import annotations

from typing import Protocol

from .model import GridCell, TerrainCell


class LogicalSpace(Protocol):
    space_id: str
    cell_size_feet: int

    def contains(self, cell: GridCell) -> bool: ...

    def cell(self, cell: GridCell) -> TerrainCell: ...

    def cells(self) -> tuple[GridCell, ...]: ...
