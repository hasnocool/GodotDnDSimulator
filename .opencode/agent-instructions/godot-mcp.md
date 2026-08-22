# Godot MCP Server — Agent Instructions

The **Godot MCP** (`godot-mcp`) is a Model Context Protocol server that gives AI assistants direct, hands-on access to Godot Engine 4.x projects. It is configured in `opencode.json` and available as a local stdio MCP server.

## Quick Reference

| Property | Value |
|----------|-------|
| **Server name** | `godot-mcp` |
| **Transport** | stdio (local) |
| **Command** | `npx -y @yanhuifair/godot-mcp -p /home/hyperion/Code/projects/GodotDnDSimulator/apps/godot-client` |
| **Project root** | `apps/godot-client/` (contains `project.godot`) |
| **Tool count** | **386** |
| **Editor plugin** | Installed at `apps/godot-client/addons/godot-mcp/` |

## Architecture & Communication Paths

The server uses **four communication paths** depending on the tool:

1. **Direct File I/O** (~250 tools) — Reads/writes `.tscn`, `.tres`, `.gd`, `.import`, `.gdshader`, `project.godot` directly. **No Godot process needed.** Fast, works offline.

2. **Godot CLI** — Spawns Godot subprocess for `run_project`, `export_project`, `launch_editor`, `get_godot_version`.

3. **Editor Bridge** (140 tools) — Connects to running Godot editor on `127.0.0.1:9876` (TCP) or via stdio fallback. Controls live editor: play/stop, breakpoints, node selection, undo/redo, scene tree, viewport, baking, plugins.

4. **Runtime Bridge** (11 tools) — Connects to `godot_mcp_runtime` autoload on `127.0.0.1:9877` inside the **running game**. Enables live scene tree inspection, method calls, input injection, **deterministic frame stepping** (`runtime_freeze` → `runtime_step` → `runtime_screenshot`).

## Bridge Connection Requirements

| Bridge | Requirement |
|--------|-------------|
| Editor | Open Godot editor with project loaded; plugin auto-enabled via `project.godot` |
| Runtime | Add `addons/godot-mcp/runtime_bridge.gd` as autoload named `godot_mcp_runtime` in Project Settings → Autoload |

**Check status:** Run `godot-mcp_get_status` — it reports `editor_bridge` and `runtime_bridge` connectivity.

## Tool Discovery

With 386 tools, **always search first**:

```bash
# Find relevant tools by keyword
godot-mcp_search_tools keyword="animation"
godot-mcp_search_tools keyword="tilemap"
godot-mcp_search_tools keyword="collision"
godot-mcp_search_tools keyword="shader graph"
```

The tool list is too large to read entirely; `search_tools` is the intended discovery mechanism.

## Common Workflows

### File-Based Scene/Resource Editing (No Editor Needed)
```bash
# Read a scene
godot-mcp_read_scene path="res://scenes/main.tscn"

# Modify a node
godot-mcp_modify_node scene_path="scenes/main.tscn" node_path="Player" properties='{"position": "Vector2(100, 200)"}'

# Create a new resource
godot-mcp_create_resource path="materials/player.tres" type="StandardMaterial3D"

# Read/write scripts
godot-mcp_read_script path="scripts/player.gd"
godot-mcp_write_script path="scripts/player.gd" content="..."
```

### Live Editor Control (Editor Must Be Open)
```bash
# Play/stop the scene
godot-mcp_editor_play
godot-mcp_editor_stop

# Node operations (all undoable via Ctrl+Z)
godot-mcp_editor_add_node type="CharacterBody2D" name="Player"
godot-mcp_editor_connect_signal node="Player" signal="body_entered" target="Enemy" method="_on_body_entered"
godot-mcp_editor_set_node_properties path="Player" properties='{"position": "Vector2(100, 200)"}'

# Debugging
godot-mcp_editor_set_breakpoint script="scripts/player.gd" line=42
godot-mcp_editor_debug_step
godot-mcp_editor_evaluate_expression expression="player.position"
```

### Live Game Runtime Control (Game Must Be Running)
```bash
# Freeze game, step frames, screenshot
godot-mcp_runtime_freeze
godot-mcp_runtime_step frames=60
godot-mcp_runtime_screenshot

# Call methods, emit signals, inject input
godot-mcp_runtime_call_method path="Player" method="take_damage" args='[10]'
godot-mcp_runtime_emit_signal path="Player" signal="health_changed" args='[90]'
godot-mcp_runtime_input keycode=87 action="press"  # W key
```

### Project Management
```bash
# Project settings
godot-mcp_read_project_config
godot-mcp_write_project_config section="application/run" key="main_scene" value="res://scenes/main.tscn"

# Input map
godot-mcp_read_input_map
godot-mcp_write_input_action action="move_left" deadzone=0.5
godot-mcp_add_input_binding action="move_left" key="A"

# Export
godot-mcp_create_export_preset name="Linux Release" platform="Linux"
godot-mcp_export_project preset="Linux Release" output_path="build/game.x86_64"
```

## Safety & Conventions

- **All editor mutations are undoable** — Every `editor_*` tool that modifies scenes uses Godot's `EditorUndoRedoManager`. One `Ctrl+Z` (or `editor_undo`) reverts the change.
- **Path traversal protection** — All file operations validate paths stay within project root.
- **Automatic backups** — Write operations on scripts/scenes create `.bak` files.
- **Read-only mode** — Set `GODOT_MCP_READ_ONLY=true` to reject all 218 write/side-effect tools.
- **Parameter normalization** — Tools accept both `snake_case` and `camelCase` (e.g., `project_path` or `projectPath`).
- **Typed errors** — Failures return structured error codes: `READ_ONLY`, `EDITOR_NOT_REACHABLE`, `EDITOR_COMMAND_FAILED`, `NOT_FOUND`, etc.

## Project-Specific Notes

- **Godot version**: 4.7.1+ (configured in `.github/workflows/ci.yml`)
- **Project structure**: `apps/godot-client/` is the Godot project root
- **Presentation-only client** — Per `AGENTS.md`, Godot client owns presentation only; authoritative simulation lives in `engine/src/godot_dnd_engine/` (Python)
- **Orthographic camera** — Main scene uses `Camera3D` with `projection = 1` (orthographic) and `CameraRig` rotated for isometric view

## Integration with AGENTS.md Rules

| AGENTS.md Rule | Godot MCP Implication |
|----------------|----------------------|
| Authoritative simulation in engine | Use MCP for **presentation** tasks only (scene setup, UI, camera, VFX). Do not implement rules logic in GDScript via MCP. |
| Deterministic RNG | Use `runtime_step` for deterministic frame-stepping during debugging; don't call `randi()` directly. |
| Spatial separation | Use `editor_create_nav_mesh`, `editor_bake_navigation` for Godot navigation; spatial authority stays in engine. |
| Data-driven mechanics | Use MCP to create resource templates (materials, themes, SpriteFrames) that engine data drives. |
| No blocking I/O | File-based tools are fast; editor/runtime tools are async via bridge. |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `EDITOR_NOT_REACHABLE` | Open Godot editor with project; verify plugin enabled in Project Settings → Plugins |
| `Runtime bridge not connected` | Add `runtime_bridge.gd` as autoload `godot_mcp_runtime`; run game from editor |
| `Project not found` | Verify `-p` path points to folder containing `project.godot` (here: `apps/godot-client`) |
| Tool not found | Run `godot-mcp_search_tools keyword="..."` to discover correct tool name |
| Permission denied | Check `GODOT_MCP_READ_ONLY` not set; verify file permissions |

## Version & Updates

- **Current**: Installed via `npx -y @yanhuifair/godot-mcp` (always latest)
- **Pinned version**: `npx @yanhuifair/godot-mcp@1.11.2 ...`
- **Upgrade plugin**: `rm -rf apps/godot-client/addons/godot-mcp && npx -y @yanhuifair/godot-mcp@latest --enable-plugin -p apps/godot-client`
- **Check version**: `npx @yanhuifair/godot-mcp --version`

## Related Files

- `AGENTS.md` — Canonical repository contract (read first)
- `docs/ARCHITECTURE.md` — Engine/Godot/tooling boundaries
- `docs/GIT_WORKFLOW.md` — Branch/commit/PR workflow
- `.github/workflows/ci.yml` — CI with Godot headless validation