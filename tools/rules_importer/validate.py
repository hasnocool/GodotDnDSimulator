# tools/rules_importer/validate.py
"""Schema and provenance validation for canonical rule entities."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from .errors import CompilationError
from .models import CanonicalEntity
from .serialization import dumps_canonical

_SCHEMA_BY_KIND = {
    "rule": "rule.schema.json",
    "action": "action.schema.json",
    "ability": "ability.schema.json",
    "condition-effect": "condition-effect.schema.json",
    "character-option": "character-option.schema.json",
    "spell": "spell.schema.json",
    "item": "item.schema.json",
    "creature": "creature.schema.json",
    "spatial-primitive": "spatial-primitive.schema.json",
}


def _entity_dict(entity: CanonicalEntity) -> dict[str, object]:
    return json.loads(dumps_canonical(entity))


def validate_entities(entities: tuple[CanonicalEntity, ...], schema_dir: Path) -> None:
    ids: set[str] = set()
    base_schema = json.loads((schema_dir / "entity-base.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(base_schema)
    base_validator = Draft202012Validator(base_schema)
    checked_kind_schemas: set[str] = set()

    for entity in entities:
        if entity.entity_id in ids:
            raise CompilationError(f"duplicate canonical entity ID: {entity.entity_id}")
        ids.add(entity.entity_id)
        try:
            schema_name = _SCHEMA_BY_KIND[entity.kind]
        except KeyError as exc:
            raise CompilationError(f"unsupported canonical entity kind: {entity.kind}") from exc

        if schema_name not in checked_kind_schemas:
            kind_schema = json.loads((schema_dir / schema_name).read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(kind_schema)
            checked_kind_schemas.add(schema_name)

        raw = _entity_dict(entity)
        errors = sorted(base_validator.iter_errors(raw), key=lambda err: list(err.path))
        if errors:
            messages = "; ".join(error.message for error in errors[:5])
            raise CompilationError(f"schema validation failed for {entity.entity_id}: {messages}")
