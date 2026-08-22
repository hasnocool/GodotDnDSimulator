# ADR 0001: Python 3.12 authoritative engine with Godot presentation client

- Status: Accepted
- Date: 2026-08-21
- Milestone: v0.1

## Context

The project needs an authoritative simulation runtime that remains usable without rendering, can power tests/tools/servers, and does not entangle rules correctness with the Godot scene tree. Godot remains the chosen 3D isometric client.

## Decision

Use Python 3.12+ for the authoritative headless engine and Godot 4.7.1+ for presentation. The engine lives under `engine/` and has no Godot rendering dependency. The Godot client lives under `apps/godot-client/` and will communicate through a versioned typed bridge/protocol introduced in a later milestone.

Initial authoritative contracts are Python dataclasses plus versioned JSON schemas for commands, events, and snapshots.

## Why Python

- Excellent fit for deterministic domain modeling, data pipelines, rules compilation, automated tests, servers, AI tooling, and future SRD ingestion.
- Keeps the engine usable by CLI/server/test processes independently of Godot.
- Strong Python 3.12 typing/tooling ecosystem.
- Allows CPU-heavy or blocking work to be isolated in worker processes/threads rather than stalling Godot's frame loop or an asyncio event loop.

## Tradeoffs

- Shipping a desktop game will eventually require packaging the Python runtime/engine or an embedded/local service strategy.
- The Godot/Python bridge adds a protocol boundary that must be versioned and tested.
- Cross-process communication has overhead compared with in-process GDScript.

These costs are accepted because the project explicitly values reusable headless simulation, server support, automated tooling, and strict separation of presentation from rules authority.

## Consequences

- Rules code must not import Godot-specific rendering APIs.
- Godot scene scripts must not become a second source of authoritative state.
- Bridge I/O must be asynchronous/non-blocking from frame-critical Godot code.
- The bridge protocol will need compatibility and reconnect/failure semantics before gameplay depends on it.
