# Spatial package

The authoritative v0.6 spatial runtime is documented in `docs/V0.6_SPATIAL_AUTHORITY.md`.

Public imports should normally come from `godot_dnd_engine.spatial` rather than individual module
paths. The package is headless and contains no Godot API dependency.

Primary entry points:

- `SpatialState` / `SquareGridSpace` for immutable logical state;
- `SpatialRuntime` for authoritative movement transitions;
- `SpatialQueryService` for read-only client/tool queries;
- `NavigationPathProposal` for validating presentation/navigation proposals;
- `move_in_encounter()` for the narrow v0.5 combat movement-budget integration;
- `SpatialEvent` / `replay_spatial()` for deterministic movement replay.

Godot scene/navigation state is never authoritative here.
