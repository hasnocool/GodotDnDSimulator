# Godot Client / Engine Bridge v1

The Godot client is a presentation and input adapter over the authoritative Python engine. This bridge exists so tactical scenes can submit intent and consume authoritative state without importing or reimplementing engine rules in GDScript.

## Authority boundary

Godot owns presentation-only state such as camera position, hover/selection, open panels, local settings, pending interaction modes, animation progress, VFX, and audio. The engine owns game/rules state, command validation, resolution, randomness, events, actor/combat state, and future spatial legality.

The client flow is:

```text
input/UI -> typed bridge request -> transport -> authoritative engine
                                      |
                                      v
                       response/snapshot/events
                                      |
                                      v
                         Godot presentation
```

No client response is authoritative until it is returned by the engine. Preview/query results are advisory read models and are invalidated by authoritative generation/sequence changes.

## Protocol envelope

Bridge protocol version 1 uses JSON objects with this common envelope:

```json
{
  "bridge_version": 1,
  "kind": "command.submit",
  "request_id": "client-request:0000000000000002",
  "correlation_id": "interaction:move-17",
  "generation": 4,
  "payload": {}
}
```

`request_id` identifies one transport request. `correlation_id` identifies the user/client interaction that caused it. `generation` lets the client reject delayed preview/query results after selection, targeting mode, or authoritative state changes have made them stale.

The repository JSON Schema is `schemas/client/v1/bridge-message.schema.json`.

## Negotiation

Every transport connection begins with `bridge.hello`. The client advertises protocol name/version and capabilities. The engine replies with `bridge.hello.accepted` plus its supported capabilities, or a rejection/incompatible version.

The Godot bridge fails closed on a protocol-version mismatch. Tactical scenes should not bypass this failure state.

Current client capabilities are:

- `commands.v1`
- `queries.v1`
- `previews.v1`
- `snapshots.v1`
- `events.v1`
- `request-cancel.v1`
- `request-generation.v1`

Capabilities are negotiation flags, not permission to invent missing engine behavior.

## Request families

### Commands

`command.submit` carries the existing versioned authoritative command envelope. It requires a stable command ID. The response is either `command.accepted` or `command.rejected`.

Accepted responses may carry an authoritative snapshot and/or ordered domain events. Rejected responses carry a categorized error with concise user wording and separate debug detail.

### Queries

`query.request` is read-only. It is used for legal-action discovery, actor inspection, current authoritative facts, resync, and future query families. Query results must not mutate authoritative state.

### Previews

`preview.request` is read-only and generation-scoped. Future v0.6 spatial previews—movement reachability, path cost, LOS, cover, targeting, AoE—will use this family instead of duplicating those calculations in Godot.

### Cancellation

Long-lived query/preview work may be cancelled. Local cancellation immediately removes the request from the pending client set and sends a best-effort `request.cancel` notice when the transport is still connected.

## Authoritative state ingestion

The bridge accepts `authoritative.snapshot` and `authoritative.events` messages, as well as snapshot/event payloads attached to successful command/query responses.

Snapshots may advance or replace the local read model but may never regress below the most recently accepted authoritative sequence.

Events are accepted only in contiguous sequence order. Duplicate/old events are ignored. A sequence gap is not guessed around: the bridge emits `resync_required` and leaves the authoritative sequence unchanged for the rejected batch.

This means scene code never needs to repair an event stream itself.

## Reconnect / resync

If a connection drops after authoritative state has been observed, the bridge remembers that a resync is required. After the next successful version/capability handshake it automatically requests `bridge.resync` starting after its last accepted authoritative sequence.

This is a presentation synchronization mechanism only. The engine remains the source of truth.

## Error categories

Protocol v1 defines:

- `validation`
- `conflict`
- `unsupported`
- `incompatible_version`
- `transport`
- `timeout`
- `cancelled`
- `stale`
- `internal`

Errors contain both `user_message` and `debug_detail`. Normal UI should prefer the concise user message while developer tooling can expose the debug detail.

## Transport abstraction

`EngineTransport` is deliberately independent of scenes and engine mechanics. `EngineBridge` depends on the abstraction, not a concrete socket implementation.

`TcpJsonTransport` provides a non-blocking local/development transport using `StreamPeerTCP`. Messages are newline-delimited JSON. It defaults to `127.0.0.1:4765` but host/port are configurable, preserving a path to a later remote/server transport without rewriting tactical scenes.

The transport is polled from the Godot frame loop; it does not use blocking connect/read loops.

`FakeEngineTransport` is deterministic and drives headless client tests without a live Python process.

## Testing

`apps/godot-client/tests/bridge_tests.gd` covers:

- protocol validation;
- compatible hello/capability negotiation;
- accepted command -> authoritative event ingestion;
- command rejection/error categorization;
- stale preview generation rejection;
- event-gap resync behavior;
- disconnect/reconnect negotiation and resync request;
- request timeout and cancellation;
- incompatible protocol failure.

Recorded snapshot/event fixtures live in `apps/godot-client/tests/fixtures/` and use the same v1 serialized contracts as the headless engine.

The CI Godot job should parse the project and execute this headless test script before client bridge work is considered complete.

## Future extension

The protocol is intentionally transport- and scene-independent. v0.6 can add spatial query/preview payloads, v0.7 can add tactical client composition, and a later server/multiplayer transport can reuse the same request/correlation/generation/state-ordering rules.
