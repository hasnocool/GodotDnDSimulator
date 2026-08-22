# Rules Ingestion and Licensing Boundary

## Purpose

This document defines how GodotDnDSimulator may fetch, transform, store, compile, and ship tabletop rules content.

The goal is to use an official, appropriately licensed rules foundation while keeping the project legally bounded, reproducible, auditable, and technically independent from source-document layout.

This is an engineering policy, not legal advice. If licensing facts change or a new source is proposed, update this document and record the evidence before importing content.

## Initial approved source

Initial target:

- **D&D System Reference Document (SRD) 5.2.1**
- Official source landing page: `https://www.dndbeyond.com/srd`
- License: **Creative Commons Attribution 4.0 International (CC BY 4.0)** for the SRD material released under that license
- License text: `https://creativecommons.org/licenses/by/4.0/`

The source manifest created by the importer must capture the exact downloaded source URL/file, retrieval date, source version, license identifier, checksum, importer version, and generated-output checksum.

Do not rely only on this prose document for provenance; generated/imported entities need machine-readable provenance.

## Explicitly excluded sources by default

Do not ingest, copy, scrape, or reconstruct content from these sources unless a compatible license/permission is separately documented and approved in-repo:

- D&D Beyond Basic Rules pages as a substitute for the SRD;
- Player's Handbook material not included in the approved SRD;
- Monster Manual material not included in the approved SRD;
- Dungeon Master's Guide material not included in the approved SRD;
- adventure books;
- setting books and protected setting lore;
- paid D&D Beyond content;
- images, maps, art, stat blocks, lore, or prose from products outside the approved licensed corpus;
- third-party websites that republish copyrighted D&D text without an independently valid license.

If an agent cannot verify that content is inside the approved licensed corpus, it must not import it.

## Trademark/branding boundary

A copyright license for SRD material does not imply permission to present this project as an official Dungeons & Dragons product or to use protected branding/settings beyond what applicable licenses permit.

Product direction:

- use an original game title/brand;
- use original world/setting names;
- use original characters, maps, art, narrative, audio, and campaign content;
- maintain clear attribution for licensed SRD-derived material;
- avoid implying Wizards of the Coast endorsement or official status.

## Source allowlist

Create a machine-readable allowlist before v0.2 completes.

Conceptual record:

```json
{
  "source_id": "wotc-srd-5.2.1",
  "display_name": "D&D SRD 5.2.1",
  "version": "5.2.1",
  "license": "CC-BY-4.0",
  "official": true,
  "allowed_for_ingestion": true,
  "source_urls": [
    "https://www.dndbeyond.com/srd"
  ]
}
```

The fetch/import tool should reject unknown source IDs by default.

Adding a source requires review of:

- owner/publisher;
- exact work/version;
- official source URL;
- license text/identifier;
- permissions needed for fetch, transform, redistribution, modification, and commercial use;
- attribution obligations;
- trademark/branding limitations;
- whether raw source may be stored in the public repository;
- whether generated derivatives may be redistributed.

## Pipeline

```text
Allowlisted source
      ↓
Fetch
      ↓
Source manifest + SHA-256
      ↓
Archive/stage permitted source representation
      ↓
Extract
      ↓
Normalize
      ↓
Parse entities/relationships
      ↓
Compile executable structures
      ↓
Schema validation
      ↓
Provenance validation
      ↓
Deterministic canonical export
      ↓
Attribution/license generation
      ↓
Coverage + unsupported-mechanics report
```

Runtime gameplay consumes canonical generated data, not the original PDF/page/HTML layout.

## Fetch stage

Requirements:

- use only approved source identifiers/URLs;
- record redirect/final source metadata where useful;
- set sensible timeout/retry behavior;
- use bounded concurrency;
- do not block async/event-loop threads;
- compute source checksum;
- avoid repeated downloads when checksum/validators indicate no change;
- make network failures explicit rather than producing partial canonical output.

Where HTTP validators such as ETag/Last-Modified are available, store them as optimization metadata, but checksums remain the stronger content identity.

## Source archive policy

Do not automatically commit raw downloaded copyrighted documents merely because the importer can fetch them.

For each approved source, document whether raw redistribution is allowed and whether the project actually needs the raw source in Git.

Preferred approach when practical:

- store source manifest/checksum in Git;
- fetch approved source in a reproducible tool step;
- keep transient raw source in ignored build/cache storage;
- commit only generated content that the license allows the project to redistribute;
- include required license/attribution files.

If a raw source is committed, its license must clearly permit that distribution and the repository should record why it is present.

## Extraction stage

The extractor should preserve structure and provenance rather than flattening the entire source into anonymous text.

Capture where available:

- heading hierarchy;
- paragraph boundaries;
- list structure;
- tables and cells;
- section identifiers;
- page/anchor/source-location metadata;
- footnotes/callouts where relevant;
- cross references.

Extraction output is an intermediate representation, not the runtime rule model.

## Normalization stage

Normalize mechanical formatting while preserving meaning and source traceability.

Examples:

- normalize whitespace;
- normalize heading levels;
- normalize table structures;
- normalize dice notation into a parser-friendly representation;
- normalize cross-reference identifiers;
- normalize units into structured values while preserving source text/reference where needed;
- normalize typographic punctuation only when it cannot alter semantics.

Do not silently “fix” ambiguous source rules during normalization. Ambiguity should become a review item.

## Entity identification

The parser/compiler should identify canonical entities such as:

- rules;
- actions/reactions;
- abilities/skills/saves;
- conditions;
- effects/modifiers/resources;
- classes/features;
- species/backgrounds;
- feats where present;
- spells;
- items/weapons/armor/equipment;
- creatures;
- movement/vision/sense primitives.

Every entity requires a stable canonical ID.

## Provenance envelope

Conceptual minimum:

```json
{
  "id": "condition.example",
  "schema_version": "1",
  "source": {
    "source_id": "wotc-srd-5.2.1",
    "document_version": "5.2.1",
    "license": "CC-BY-4.0",
    "section": "Rules Glossary",
    "source_location": "...",
    "source_sha256": "..."
  },
  "generator": {
    "name": "rules-importer",
    "version": "..."
  }
}
```

Exact schema will be versioned in `schemas/`.

## Stable IDs

IDs should not depend solely on page number or source ordering because upstream layout can change.

Prefer a documented scheme based on:

- entity category;
- normalized canonical name/slug;
- namespace/ruleset when needed;
- explicit collision handling.

Changing a stable entity ID after saves/content packs depend on it is a migration event and requires mapping/tests.

## Rule compilation

Do not make runtime behavior depend on free-form prose interpretation.

Compile mechanics into structures such as:

```text
Trigger
Requirements
Costs
Target selector
Range/area
Roll/check/save
Modifiers
Outcome branches
Effects
Duration
Concentration/ongoing state
Reaction/event hooks
```

The source text/reference may be retained for UI/reference if licensed and useful, but executable semantics should be typed and validated.

## Unsupported mechanics

Unsupported mechanics must be visible.

The compiler should classify entities/mechanics as something like:

- executable;
- data-only;
- partially executable;
- unsupported;
- requires manual review.

Generate a report such as:

```text
Imported entities:        2,400
Executable:               1,900
Data-only:                  350
Partial:                    100
Unsupported:                 40
Manual review:               10
```

Also group unsupported primitives, for example:

```text
summoning        11
teleport          7
shapechange       3
special sense     2
```

Never silently approximate unsupported rules.

## Validation

Fail generation when:

- schemas are invalid;
- required provenance is missing;
- source IDs are not approved;
- stable IDs collide unexpectedly;
- references point to missing entities;
- generated output is non-deterministic without an explicitly documented reason;
- attribution/license generation fails;
- source checksum differs from an expected/pinned value in a mode that requires review.

Warnings may be used for explicitly non-blocking coverage gaps, but unsupported mechanics must remain visible.

## Deterministic output

Given identical:

- source bytes;
- importer/compiler version;
- configuration;
- schemas;

the canonical generated output should be byte-for-byte deterministic where practical.

Use stable ordering and normalized serialization. Do not embed wall-clock timestamps in canonical entity files if they would make output non-reproducible; keep retrieval/build timestamps in manifests/reports that are intentionally variable.

## Version diffing

The importer toolchain should compare two canonical source versions.

Report:

- added entities;
- removed entities;
- changed entities;
- unchanged entities;
- source text/provenance changes;
- executable/mechanical representation changes;
- stable-ID changes;
- new unsupported primitives;
- compatibility/migration concerns.

This is the primary workflow for upstream errata/new SRD versions.

## Update process for a new SRD/errata version

1. Verify the new official source and license.
2. Add/update allowlist entry.
3. Fetch and record checksum.
4. Run extraction/compile/validation.
5. Run canonical diff against current supported version.
6. Review mechanical changes and unsupported primitives.
7. Add/update runtime primitives and conformance tests.
8. Regenerate canonical data deterministically.
9. Update attribution/licenses.
10. Update `CHANGELOG.md`, `TODO.md`, compatibility notes, and rules coverage.
11. Merge through a focused PR.

Do not overwrite the previous source version in a way that prevents existing saves/content packs from identifying what ruleset they used.

## Runtime ruleset identity

Campaign/save metadata should eventually include:

- ruleset ID;
- ruleset/source version;
- canonical content pack version/checksum;
- schema versions;
- required extension/content packs.

This allows a save to state what rules it was created under.

## Attribution

The build/release process should generate or include required attribution for licensed SRD-derived material.

Keep attribution separate enough that it cannot be accidentally removed when original game credits are edited.

At minimum, the repository should maintain:

- license identifier/text or appropriate link/copy as required;
- attribution notice required by the applicable license;
- source/version identity;
- indication of modifications/adaptations where required.

Final exact wording should be reviewed against the applicable SRD notice/license before release.

## AI rules-content safety

LLMs may help transform already-approved licensed source content, but they must not be used to reconstruct non-approved copyrighted rulebook text from memory or web sources.

When an AI suggests a rule:

- treat it as untrusted until traced to approved source data or identified as original project content;
- never label generated text as SRD-derived without provenance;
- do not use an LLM to fill gaps in imported official content unless the output is explicitly original/homebrew and kept separate.

## Original/homebrew content

Original project mechanics and content are encouraged but must be namespaced/separated from imported SRD material.

Each original entity should identify something like:

- source type: `original`;
- owning pack;
- project/creator license;
- dependencies on SRD primitives/entities.

This makes it possible to distinguish licensed upstream material from project-owned extensions.

## Definition of done for rules ingestion work

A rules-import PR is not complete until applicable items are true:

- source is allowlisted and licensed;
- checksums/provenance are recorded;
- extraction is reproducible;
- schemas validate;
- generated output is deterministic;
- unsupported mechanics are reported;
- conformance/runtime follow-ups are in `TODO.md`;
- attribution/licensing output is correct;
- source-version diff is reviewed when updating an existing ruleset;
- `CHANGELOG.md` documents the rules/content change;
- no excluded/non-approved copyrighted source material was introduced.
