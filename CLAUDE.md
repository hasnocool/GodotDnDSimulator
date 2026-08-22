# Claude Instructions

`AGENTS.md` is the canonical repository contract. Read and obey it before making changes.

Also read `ROADMAP.md`, `TODO.md`, `CHANGELOG.md`, and the relevant documents under `docs/` before implementation.

For any task that touches `apps/godot-client/**`, **before editing** also read and obey:

- `apps/godot-client/AGENTS.md` — client-specific authority, architecture, bridge, testing, performance, and UX contract;
- `apps/godot-client/TODO.md` — detailed client execution backlog subordinate to the root roadmap/TODO.

Claude-specific reminders:

- Do not infer rules from memory when approved canonical/source data exists; inspect the repository source/provenance first.
- Do not reconstruct non-approved D&D rulebook content.
- Prefer small, reviewable edits tied to one milestone/TODO.
- Never let Godot presentation code become authoritative game state.
- Route all randomness through deterministic project abstractions.
- Add regression/conformance tests for behavioral changes.
- Update `TODO.md`, `CHANGELOG.md`, and relevant docs in the same PR; for client work also keep `apps/godot-client/TODO.md` synchronized.
- Use a feature/fix/docs/refactor/chore/test branch; do not develop directly on `main`.
- Before reporting completion, inspect the final diff and state exactly what tests ran.

If this file conflicts with `AGENTS.md`, `AGENTS.md` wins. Within `apps/godot-client/**`, the local client `AGENTS.md` may add stricter requirements but may not weaken the root contract.
