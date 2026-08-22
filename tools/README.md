# Tools

Development-time importers, compilers, validators, migrations, and conformance tooling belong here. Runtime gameplay must not depend on this directory.

## Rules importer

`tools/rules_importer/` implements the v0.2 licensed SRD ingestion pipeline.

Common commands:

```bash
# Fetch and verify the production allowlisted SRD source.
python -m tools.rules_importer.cli fetch

# Fetch/reuse cache, extract, normalize, compile, validate, and export.
python -m tools.rules_importer.cli build

# Prove deterministic generated output using the checked-in synthetic fixture.
python -m tools.rules_importer.smoke
```

Source policy is machine-readable in `config/rules/sources.json`. Raw downloaded sources are cached under ignored `.cache/` paths and must not be committed casually.

See `docs/V0.2_RULES_PIPELINE.md` and `docs/RULES_INGESTION.md` before changing source policy, provenance, canonical IDs, schemas, or attribution behavior.
