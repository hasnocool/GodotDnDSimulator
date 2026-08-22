# ADR 0002: Semantic versioning and serialized contract versions

- Status: Accepted
- Date: 2026-08-21
- Milestone: v0.1

## Decision

Use Semantic Versioning for repository releases. Before 1.0, milestone releases may introduce breaking APIs, but any breaking save/event/command/content-schema change must still be explicit in `CHANGELOG.md` and accompanied by migration or a clearly documented compatibility break.

Serialized contracts have independent integer schema versions. v0.1 begins with:

- command envelope schema: v1;
- event envelope schema: v1;
- snapshot schema: v1;
- deterministic RNG algorithm identifier: `pcg32-v1`.

Changing RNG behavior, stable ID meaning, or serialized interpretation is a compatibility change even when Python type signatures stay the same.

## Release process

1. Finish milestone exit criteria.
2. Run the full test/static/schema/Godot validation suite.
3. Verify rules/content licenses and attribution.
4. Move applicable `Unreleased` entries to a dated version section.
5. Update version metadata consistently.
6. Tag the release.
7. Build artifacts from the tagged commit.

## Rationale

Repository version numbers alone are insufficient for long-lived campaigns and deterministic replays. Independent schema and algorithm identifiers let migrations distinguish file-format evolution from normal code releases.
