# ADR 0003: Namespaced stable identifiers

- Status: Accepted
- Date: 2026-08-21
- Milestone: v0.1

## Decision

Serialized domain identifiers use explicit namespaces. Initial reserved namespaces are:

- `campaign:`
- `session:`
- `actor:`
- `command:`
- `event:`
- `rule:`
- `effect:`
- `pack:`

IDs are opaque identifiers. Code must not infer gameplay properties from their text beyond the namespace.

Event ordering is represented separately by the event `sequence`. v0.1 deterministic event IDs use `event:<zero-padded-sequence>` within a campaign/session stream; campaign/session identity remains part of the event envelope.

## Consequences

- Imported rules and packs can keep separate ownership/provenance while sharing engine primitives.
- Invalid or cross-domain IDs fail early at command/event boundaries.
- A future globally unique event ID format can be introduced with a schema/version migration without changing sequence semantics.
