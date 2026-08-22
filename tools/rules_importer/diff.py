# tools/rules_importer/diff.py
"""Canonical entity diffing for upstream SRD/errata updates."""

from __future__ import annotations

from dataclasses import replace

from .models import CanonicalEntity, EntityDiff
from .serialization import dumps_canonical


def _without_prose(entity: CanonicalEntity) -> CanonicalEntity:
    return replace(entity, source_text="")


def diff_entities(
    old: tuple[CanonicalEntity, ...],
    new: tuple[CanonicalEntity, ...],
) -> EntityDiff:
    old_map = {entity.entity_id: entity for entity in old}
    new_map = {entity.entity_id: entity for entity in new}
    old_ids = set(old_map)
    new_ids = set(new_map)
    added = sorted(new_ids - old_ids)
    removed = sorted(old_ids - new_ids)
    changed: list[str] = []
    unchanged: list[str] = []
    prose_only: list[str] = []
    mechanical: list[str] = []
    for entity_id in sorted(old_ids & new_ids):
        before = old_map[entity_id]
        after = new_map[entity_id]
        if dumps_canonical(before) == dumps_canonical(after):
            unchanged.append(entity_id)
            continue
        changed.append(entity_id)
        if dumps_canonical(_without_prose(before)) == dumps_canonical(_without_prose(after)):
            prose_only.append(entity_id)
        else:
            mechanical.append(entity_id)
    return EntityDiff(
        added=tuple(added),
        removed=tuple(removed),
        changed=tuple(changed),
        unchanged=tuple(unchanged),
        prose_only_changed=tuple(prose_only),
        mechanical_changed=tuple(mechanical),
    )
