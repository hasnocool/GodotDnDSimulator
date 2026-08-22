# tools/rules_importer/validate.py
"""Schema and provenance validation for canonical rule entities."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

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
    value = json.loads(dumps_canonical(entity))
    if not isinstance(value, dict):
        raise CompilationError("canonical entity did not serialize to a JSON object")
    return value


def _validator(schema_dir: Path, schema_name: str) -> Draft202012Validator:
    base_schema = json.loads((schema_dir / "entity-base.schema.json").read_text(encoding="utf-8"))
    kind_schema = json.loads((schema_dir / schema_name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(base_schema)
    Draft202012Validator.check_schema(kind_schema)
    base_id = base_schema.get("$id")
    if not isinstance(base_id, str) or not base_id:
        raise CompilationError("base entity schema must define a non-empty $id")
    registry = Registry().with_resource(base_id, Resource.from_contents(base_schema))
    return Draft202012Validator(kind_schema, registry=registry)


def validate_entities(entities: tuple[CanonicalEntity, ...], schema_dir: Path) -> None:
    ids: set[str] = set()
    validators: dict[str, Draft202012Validator] = {}

    for entity in entities:
        if entity.entity_id in ids:
            raise CompilationError(f"duplicate canonical entity ID: {entity.entity_id}")
        ids.add(entity.entity_id)
        try:
            schema_name = _SCHEMA_BY_KIND[entity.kind]
        except KeyError as exc:
            raise CompilationError(f"unsupported canonical entity kind: {entity.kind}") from exc
        validator = validators.get(schema_name)
        if validator is None:
            validator = _validator(schema_dir, schema_name)
            validators[schema_name] = validator
        errors = sorted(validator.iter_errors(_entity_dict(entity)), key=lambda err: list(err.path))
        if errors:
            messages = "; ".join(error.message for error in errors[:5])
            raise CompilationError(f"schema validation failed for {entity.entity_id}: {messages}")
