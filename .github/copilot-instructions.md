# GitHub Copilot Repository Instructions

Read and follow `/AGENTS.md` as the canonical project contract before proposing or changing code.

Always align work with `/ROADMAP.md` and `/TODO.md`, and keep `/CHANGELOG.md` plus relevant `/docs` synchronized.

## Non-negotiable architecture

- Authoritative game/rules state belongs in the headless engine, not Godot UI/scene scripts.
- Use `Command -> Validation -> Resolution -> Events -> Reducer -> New State`.
- All randomness goes through deterministic project RNG/dice abstractions.
- Prefer generic triggers/requirements/targets/modifiers/effects over named spell/item/monster conditionals.
- Spatial legality must be headlessly testable; Godot navigation is an adapter, not the rules authority.
- AI/LLMs may submit typed commands but never directly mutate game state.

## Rules/content

- Only use rules sources approved by `docs/RULES_INGESTION.md`.
- Do not scrape/reconstruct non-SRD D&D books or D&D Beyond Basic Rules.
- Preserve source/version/license/checksum provenance on imported entities.
- Keep original/homebrew content clearly separated/namespaced from SRD-derived content.

## Engineering

- Do not block async/event-loop or frame-critical paths with disk/network/database/subprocess/CPU-heavy work.
- Use thread-safe communication/shared-state patterns.
- Add tests for behavioral changes and regression tests for bug fixes.
- Do not hand-edit generated rules/content owned by a generator.
- Validate untrusted packs, imports, network input, and AI tool arguments.

## Git

- Do not develop substantive changes directly on `main`.
- Use focused branches and Conventional Commit-style messages.
- Avoid unrelated refactors in feature PRs.
- Update TODO/changelog/docs in the same PR.
- Inspect the final diff and test results before declaring completion.

If any instruction here conflicts with `/AGENTS.md`, `/AGENTS.md` wins.
