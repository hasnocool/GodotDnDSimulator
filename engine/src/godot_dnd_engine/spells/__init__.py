# engine/src/godot_dnd_engine/spells/__init__.py
"""Generic deterministic v0.8 spell runtime."""

from .events import (
    SPELL_EVENT_SCHEMA_VERSION,
    SpellEvent,
    spell_event_from_dict,
    spell_event_to_dict,
    spell_events_jsonl,
)
from .model import (
    ConcentrationState,
    SaveEffect,
    SpellDefinition,
    SpellEffectKind,
    SpellEffectSpec,
    SpellResolution,
    SpellScaling,
    SpellSlotPool,
    SpellTargetKind,
    SpellcastingState,
)
from .query import SpellQueryService
from .runtime import ConcentrationCheck, SpellRuntime, SpellTargetOutcome, SpellTransition
from .state import ActiveSpellEffect, SpellRuntimeState

__all__ = [
    "SPELL_EVENT_SCHEMA_VERSION",
    "ActiveSpellEffect",
    "ConcentrationCheck",
    "ConcentrationState",
    "SaveEffect",
    "SpellDefinition",
    "SpellEffectKind",
    "SpellEffectSpec",
    "SpellEvent",
    "SpellQueryService",
    "SpellResolution",
    "SpellRuntime",
    "SpellRuntimeState",
    "SpellScaling",
    "SpellSlotPool",
    "SpellTargetKind",
    "SpellTargetOutcome",
    "SpellTransition",
    "SpellcastingState",
    "spell_event_from_dict",
    "spell_event_to_dict",
    "spell_events_jsonl",
]
