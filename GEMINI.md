# Gemini Instructions

`AGENTS.md` is the canonical repository contract. Read and obey it before making changes.

Read `ROADMAP.md`, `TODO.md`, `CHANGELOG.md`, and relevant `docs/` before implementation.

For any task that touches `apps/godot-client/**`, **before editing** also read and obey:

- `apps/godot-client/AGENTS.md` — client-specific authority, architecture, bridge, testing, performance, and UX contract;
- `apps/godot-client/TODO.md` — detailed client execution backlog subordinate to the root roadmap/TODO.

Gemini-specific reminders:

- Ground rule/content work in approved repository provenance; do not fill official-rule gaps from model memory.
- Keep imported SRD-derived data separate from original/homebrew content.
- Preserve command -> validation -> resolution -> events -> reducer -> state architecture.
- Godot scenes/UI may present state and submit commands, but may not own authoritative rules outcomes.
- Use deterministic RNG/dice abstractions only.
- Treat network, pack, importer, and AI inputs as untrusted and validate them.
- Keep async/event-loop and frame-critical paths free of blocking disk/network/database/subprocess work.
- Add or update tests for every meaningful behavior change.
- Keep TODO/changelog/docs synchronized in the same PR; for client work also keep `apps/godot-client/TODO.md` synchronized.
- Work on focused branches and inspect the complete diff before completion.

If this file conflicts with `AGENTS.md`, `AGENTS.md` wins. Within `apps/godot-client/**`, the local client `AGENTS.md` may add stricter requirements but may not weaken the root contract.
