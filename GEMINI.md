# Gemini Instructions

`AGENTS.md` is the canonical repository contract. Read and obey it before making changes.

Read `ROADMAP.md`, `TODO.md`, `CHANGELOG.md`, and relevant `docs/` before implementation.

When a task touches anything under `apps/godot-client/**`, also read and obey `apps/godot-client/AGENTS.md` and `apps/godot-client/TODO.md` before editing client files. Root roadmap/TODO remain milestone authority; the client TODO is the detailed execution backlog.

Gemini-specific reminders:

- Ground rule/content work in approved repository provenance; do not fill official-rule gaps from model memory.
- Keep imported SRD-derived data separate from original/homebrew content.
- Preserve command -> validation -> resolution -> events -> reducer -> state architecture.
- Godot scenes/UI may present state and submit commands, but may not own authoritative rules outcomes.
- Use deterministic RNG/dice abstractions only.
- Treat network, pack, importer, and AI inputs as untrusted and validate them.
- Keep async/event-loop and frame-critical paths free of blocking disk/network/database/subprocess work.
- Add or update tests for every meaningful behavior change.
- Keep root TODO/changelog/docs and the client TODO synchronized in the same PR when applicable.
- Work on focused branches and inspect the complete diff before completion.

If this file conflicts with `AGENTS.md`, `AGENTS.md` wins.
