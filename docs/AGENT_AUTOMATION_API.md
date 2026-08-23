# Agent Playtesting, AI Control, and Godot UI Debugging API

## Purpose

v1.0.1 adds provider-neutral automation surfaces for three related needs:

- let AI policies control other party members, the hero, and tactical NPC/enemy actors;
- play the original Lanterns Below test campaign end to end automatically for deterministic testing;
- let a debugging agent inspect and interact with the real Godot UI, collect logs, and capture
  screenshots in the same way a human tester would drive the client.

These surfaces do **not** move gameplay authority into AI code or Godot. The authoritative Python
runtime still validates every command, spatial decision, combat result, world transition, and random
outcome.

## Architecture

```text
                       structured observation
Authoritative engine  ─────────────────────────►  AI / test policy
       ▲                                            │
       │                                            │ choose token
       │              legal action tokens           ▼
       └──────────────────────────────────────  agent.execute
                       typed command                 │
       ▲                                             │
       └──────── normal bridge validation ◄──────────┘

Godot UI ◄── localhost UI automation RPC ── debugging agent
   │
   ├── visible control-tree snapshot
   ├── focus / activate / click
   ├── registered input actions
   ├── editable text
   ├── screenshot capture
   └── structured ClientLog retrieval
```

The engine API and UI API are complementary. An AI gameplay policy can use the engine API directly
for fast simulation. A debugging agent can use the Godot API when it needs to reproduce a real
presentation/input problem.

## Engine agent API

The default `godot-dnd-client-bridge` entry point now runs the agent-aware playable-world bridge. It
keeps every existing bridge capability and additionally advertises:

```text
agent.observations.v1
agent.legal-actions.v1
agent.control.v1
agent.execute.v1
```

The agent API uses the existing bridge v1 envelopes. No second transport protocol is introduced.

### Observe

Send a normal `query.request` with:

```json
{
  "query_type": "agent.observe",
  "query": {}
}
```

The result conforms to `schemas/agent/v1/agent-observation.schema.json` and includes:

- world state;
- active tactical state when an encounter is running;
- current actor and its controller assignment;
- all known actor control assignments;
- a freshly generated list of legal action tokens.

Each legal action includes:

```json
{
  "action_id": "agent-action:17:0123456789abcdef",
  "label": "Strike actor:enemy",
  "command_type": "tactical.attack",
  "actor_id": "actor:premade-mira",
  "payload": {"target_id": "actor:enemy"},
  "expected_sequence": 17,
  "context": "tactical",
  "metadata": {"kind": "attack"}
}
```

The action ID is derived from the action content and authoritative sequence. It is therefore a
short-lived capability token, not a permanent action identifier.

### Query only the legal actions

```json
{
  "query_type": "agent.actions",
  "query": {}
}
```

### Query controller assignments

```json
{
  "query_type": "agent.controllers",
  "query": {}
}
```

### Assign AI or human control

Submit a normal bridge command with command type `agent.set_control` and payload:

```json
{
  "actor_id": "actor:premade-mira",
  "mode": "agent",
  "policy_id": "my-llm-policy"
}
```

Supported modes are:

- `human` — actor-scoped action tokens cannot be executed by the agent service;
- `agent` — actor-scoped action tokens may be executed by the agent service.

Party characters default to `human`. Non-party tactical actors default to `agent`. The hero is not
special: it can be switched to `agent` exactly like any other party member, which is what automated
campaign tests do.

Controller assignment is orchestration metadata. It does not modify character statistics, world
state, combat state, or replay state.

### Execute a legal action token

Submit command type `agent.execute`:

```json
{
  "action_id": "agent-action:17:0123456789abcdef"
}
```

Before execution, the service recomputes the legal-action list from the current authoritative state.
The request is rejected when the token is stale, unknown, no longer legal, or belongs to a
human-controlled actor. A valid token is converted back into the normal typed command and submitted
through the ordinary bridge validation path.

This means an LLM cannot bypass the rules by inventing coordinates, targets, prices, spell slots,
or state mutations. It can only choose among engine-produced actions.

## What actions are exposed

The v1.0.1 adapter currently produces legal tokens for the implemented test-campaign surface:

### World

- start campaign with the premade party;
- start dialogue and choose currently available dialogue choices;
- travel through currently available exits;
- resolve interactions using a party actor;
- begin authored encounters;
- buy and sell currently valid shop items;
- equip owned items into engine-declared compatible slots;
- rest when available;
- record an encounter only after the bound tactical stream reports a party victory.

### Tactical

- legal training strikes after authoritative attack preview;
- legal spell casts after `spells.available` plus `spells.preview` validation;
- every authoritative reachable movement destination;
- end turn.

This is a generic control boundary. More sophisticated tactical scoring, goals, memories, planning,
social policy, or LLM prompts belong to the future AI milestones and should consume these same
observations/actions rather than receive privileged engine access.

## Deterministic full-campaign autoplay

Run the included baseline policy with:

```bash
godot-dnd-agent-autoplay --seed 23 --max-steps 2000
```

or:

```bash
python -m godot_dnd_engine.agent_autoplay --seed 23 --max-steps 2000
```

The baseline intentionally favors repeatability over difficulty:

- all four premade heroes are switched to agent control;
- party actors prefer a legal hostile Arc Lance, then a legal strike, then movement, then end turn;
- tactical NPC/enemy actors are still agent-controlled but use a deterministic passive end-turn
  policy in this regression scenario;
- the world policy accepts the quarry mission, exercises shop buy/equip/rest/sell, resolves the
  campaign interactions, chooses the keep-lantern branch, completes all four tactical encounters,
  and stops only after `flag:campaign-complete`.

That passive opponent policy is only a stable regression fixture. It is not the intended production
NPC AI.

Optional trace output:

```bash
godot-dnd-agent-autoplay \
  --seed 23 \
  --trace-json .logs/godot-dnd/lanterns-trace.json
```

The same seed produces the same action trace and final observation as long as the authoritative
contracts and baseline policy are unchanged.

## Structured disk diagnostics

### Engine / agent

The agent-aware bridge defaults to:

```text
.logs/godot-dnd/engine-<UTC timestamp>.jsonl
```

The autoplay CLI defaults to:

```text
.logs/godot-dnd/autoplay-<UTC timestamp>.jsonl
```

Use another directory:

```bash
godot-dnd-client-bridge --log-dir /tmp/godot-dnd-debug
```

Disable engine disk diagnostics:

```bash
godot-dnd-client-bridge --no-disk-log
```

Engine diagnostics are written by a bounded background JSONL writer so filesystem latency does not
block the asyncio bridge loop. Records contain timestamps, categories, operation names, action IDs,
actor IDs, sequences, success/rejection state, and other structured diagnostic fields. Raw
credentials/tokens are not intentionally recorded.

`.logs/` is ignored by Git.

### Godot client

`ClientLog` still keeps its bounded in-memory history and now asynchronously writes JSONL under:

```text
user://logs/client-<UTC timestamp>.jsonl
```

The live path is returned by `ClientLog.disk_log_path()` and by the UI automation status/snapshot/log
methods.

## Godot UI automation/debug API

The UI API is **disabled by default**.

Enable it when launching Godot:

```bash
GODOT_DND_UI_AUTOMATION=1 \
GODOT_DND_UI_AUTOMATION_TOKEN='local-debug-token' \
godot --path apps/godot-client
```

or include the Godot user argument:

```text
--ui-automation
```

Default endpoint:

```text
127.0.0.1:4766
```

Override the port with `GODOT_DND_UI_AUTOMATION_PORT`.

The service always binds to loopback. Setting a token is strongly recommended whenever other local
processes are not fully trusted.

Requests are newline-delimited JSON and conform to
`schemas/client/v1/ui-automation-request.schema.json`:

```json
{
  "id": "debug-1",
  "token": "local-debug-token",
  "method": "ui.snapshot",
  "params": {}
}
```

Response:

```json
{
  "id": "debug-1",
  "ok": true,
  "result": {}
}
```

### Supported methods

| Method | Purpose |
| --- | --- |
| `automation.status` | Endpoint status, port, token requirement, client log path |
| `ui.snapshot` | Visible `Control` tree, text, bounds, focus, shell state, authoritative sequence |
| `ui.inspect` | Inspect one visible `Control` by absolute `/root/...` path |
| `ui.focus` | Give one visible `Control` GUI focus |
| `ui.activate` | Activate a control through viewport mouse input at its center |
| `ui.click_at` | Inject a left mouse click at viewport coordinates |
| `ui.set_text` | Set a visible editable `LineEdit` or `TextEdit` |
| `ui.input_action` | Inject a registered Godot `InputMap` action press/release |
| `ui.logs` | Retrieve recent structured `ClientLog` entries and disk path |
| `ui.screenshot` | Capture the live viewport to `user://logs/screenshots/` |

There is deliberately no `ui.call_method`, arbitrary script evaluation, arbitrary file read/write,
or engine-state mutation method.

## Python UI client

Agents can use the built-in Python client:

```python
from godot_dnd_engine.ui_automation_client import UiAutomationClient

with UiAutomationClient(token="local-debug-token") as ui:
    snapshot = ui.snapshot()
    ui.activate("/root/GodotDnDSimulator/AppShell/SomeButton")
    logs = ui.logs(limit=200)
    screenshot = ui.screenshot()
```

One-off CLI call:

```bash
godot-dnd-ui-automation ui.snapshot --token local-debug-token
```

With params:

```bash
godot-dnd-ui-automation ui.activate \
  --token local-debug-token \
  --params-json '{"path":"/root/GodotDnDSimulator/AppShell/SomeButton"}'
```

The Python client is restricted to loopback hosts as an additional guardrail.

## Recommended debugging-agent loop

A debugging agent should use this sequence:

1. launch `godot-dnd-client-bridge` with disk diagnostics enabled;
2. launch Godot with the UI automation API enabled and a local token;
3. call `ui.snapshot` and inspect visible text, control paths, focus, shell state, and authoritative
   sequence;
4. interact through `ui.activate`, `ui.click_at`, `ui.set_text`, or `ui.input_action`;
5. after each meaningful action, snapshot again and inspect `ui.logs`;
6. capture `ui.screenshot` whenever visual state is part of the failure;
7. correlate Godot client entries with engine JSONL entries using request IDs, correlation/action IDs,
   actor IDs, and authoritative sequence numbers;
8. reproduce the smallest failing interaction before modifying code;
9. rerun the same interaction after the fix.

This makes UI debugging observable and reproducible while still testing the actual Godot input and
presentation layer.

## Testing

Python coverage includes:

- observation/action shape;
- hero AI-control assignment;
- human-control enforcement;
- stale legal-action token rejection;
- versioned observation schema validation;
- JSONL diagnostic persistence;
- local Python UI-client framing;
- deterministic complete Lanterns Below autoplay and same-seed trace parity.

Godot headless coverage includes visible UI snapshotting, focus, button activation through viewport
input, editable text, fail-closed unknown paths, and structured log retrieval.

The repository still distinguishes implementation coverage from an actual interactive desktop agent
session. A real executable Godot/UI-agent playthrough remains an evidence gate until it is run on a
working integrated environment.
