# Claude Instructions

`AGENTS.md` is the canonical repository contract. Read and obey it before making changes.

Also read `ROADMAP.md`, `TODO.md`, `CHANGELOG.md`, and the relevant documents under `docs/` before implementation.

Claude-specific reminders:

- Do not infer rules from memory when approved canonical/source data exists; inspect the repository source/provenance first.
- Do not reconstruct non-approved D&D rulebook content.
- Prefer small, reviewable edits tied to one milestone/TODO.
- Never let Godot presentation code become authoritative game state.
- Route all randomness through deterministic project abstractions.
- Add regression/conformance tests for behavioral changes.
- Update `TODO.md`, `CHANGELOG.md`, and relevant docs in the same PR.
- Use a feature/fix/docs/refactor/chore/test branch; do not develop directly on `main`.
- Before reporting completion, inspect the final diff and state exactly what tests ran.

If this file conflicts with `AGENTS.md`, `AGENTS.md` wins.
