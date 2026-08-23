# ADR 0004: Agent control and UI automation

## Status

Accepted for v1.0.1.

## Context

The project needs AI-controlled party members, heroes, NPC/combatants, deterministic automated
campaign playthroughs, and a debugging agent that can inspect and operate the Godot client like a
human tester. Those capabilities must not create a second rules engine or allow an AI/provider to
mutate authoritative state directly.

## Decision

Use two narrow, complementary automation boundaries:

1. **Engine agent API.** AI policies receive versioned structured observations and a freshly computed
   list of legal action tokens. An agent submits a token, not arbitrary gameplay mutation data. The
   service recomputes the legal list, rejects stale/unknown tokens, verifies actor control ownership,
   and routes the selected typed command through the normal authoritative bridge.
2. **Godot UI automation API.** An opt-in localhost-only RPC exposes visible UI inspection, focus,
   activation/clicks, editable text, registered input actions, structured client logs, and
   screenshots. It does not expose arbitrary method execution and it does not directly mutate engine
   state.

Party actors default to human control. Non-party tactical combatants default to agent control. Any
known actor, including the hero, can be explicitly switched between `human` and `agent` control.

A provider-neutral deterministic baseline policy is included only for regression testing. More
advanced utility/planning/LLM behavior remains future v1.4+ AI work and must use the same legal-action
boundary.

Structured diagnostics are written as JSONL on both sides. Engine/agent writes use a bounded
background queue so disk latency does not block the bridge loop. Godot `ClientLog` retains an
in-memory window while asynchronously persisting the same diagnostic stream under `user://logs/`.

## Consequences

- AI, scripted tests, human clients, and future remote agents share the same authoritative command
  validation path.
- Stale observations cannot be converted into unchecked commands because action tokens include the
  current authoritative sequence and are recomputed before execution.
- The full original test campaign can be played headlessly by deterministic agents.
- A debugging agent can inspect and interact with the real Godot control tree without privileged
  access to reducers or runtime state mutation.
- UI automation is disabled by default, binds only to loopback, and can require an explicit token.
- Future AI sophistication can change policy/planning without changing rules authority or the client
  boundary.
