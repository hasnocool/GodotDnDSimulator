# GodotDnDSimulator v1.0 credits

## Project

**GodotDnDSimulator** is an original headless tabletop-RPG simulation project with a Godot presentation client.

The v1.0 adventure **Lanterns Below** — including its named locations, characters, dialogue, encounters, quest framing, and project-specific items — is original project content.

## Rules and licensed content

The repository supports importing approved licensed SRD material through its provenance-aware rules pipeline. Any release that includes generated licensed rules/content must include the matching attribution output from the repository `LICENSES/` directory and the generated attribution bundle associated with that dataset.

The repository currently tracks `LICENSES/SRD-5.2.1-ATTRIBUTION.txt` for the configured SRD source policy. Inclusion of that attribution file in a release package does not by itself mean a full audited SRD dataset was bundled; release builders must still verify the actual content provenance used by that build.

## Godot Engine

The client is built for Godot 4.x. Godot Engine is distributed under the MIT license. If a release bundle includes a Godot engine binary or exported executable containing engine code, the distributor must include the applicable Godot license/copyright notice with that binary distribution.

The repository's deterministic source-bundle builder packages the Godot project resources but does not itself redistribute the Godot editor or engine binary.

## Architecture credit

Rules, world state, spatial legality, tactical resolution, randomness, save validation, and deterministic replay are owned by the Python engine. The Godot client presents authoritative data and submits typed player intent rather than duplicating gameplay authority.
