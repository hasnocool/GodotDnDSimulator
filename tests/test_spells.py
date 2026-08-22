# tests/test_spells.py
from __future__ import annotations

import json

import pytest

from godot_dnd_engine.errors import ValidationError
from godot_dnd_engine.models import CommandEnvelope
from godot_dnd_engine.rules.targets import TargetMode, TargetSelector
from godot_dnd_engine.spell_slice import SpellEnabledTacticalSession
from godot_dnd_engine.spells import (
    SpellDefinition,
    SpellEffectKind,
    SpellEffectSpec,
    SpellEvent,
    SpellResolution,
    SpellTargetKind,
    spell_event_from_dict,
    spell_event_to_dict,
    spell_events_jsonl,
)


def _session(seed: int = 7) -> SpellEnabledTacticalSession:
    return SpellEnabledTacticalSession.create(
        campaign_id="campaign:spell-tests",
        session_id="session:spell-tests",
        seed=seed,
    )


def _command(
    session: SpellEnabledTacticalSession,
    actor_id: str,
    command_type: str,
    payload: dict[str, object],
    index: int,
) -> CommandEnvelope:
    return CommandEnvelope(
        command_id=f"command:spell-test-{index}",
        campaign_id="campaign:spell-tests",
        session_id="session:spell-tests",
        command_type=command_type,
        payload=payload,
        actor_id=actor_id,
        expected_sequence=session.sequence,
    )


def _other_actor(session: SpellEnabledTacticalSession, actor_id: str) -> str:
    return next(
        item.actor.actor_id
        for item in session.encounter.combatants
        if item.actor.actor_id != actor_id
    )


def _end_until_turn(
    session: SpellEnabledTacticalSession,
    actor_id: str,
    start_index: int,
) -> int:
    index = start_index
    if session.encounter.current_actor_id == actor_id:
        current = actor_id
        session.handle_command(_command(session, current, "tactical.end_turn", {}, index))
        index += 1
    while session.encounter.current_actor_id != actor_id:
        current = session.encounter.current_actor_id
        assert current is not None
        session.handle_command(_command(session, current, "tactical.end_turn", {}, index))
        index += 1
    return index


def test_spell_snapshot_and_available_query_are_data_driven() -> None:
    session = _session()
    current = session.encounter.current_actor_id
    assert current is not None

    snapshot = session.snapshot()["state"]["tactical"]["spellcasting"]
    assert snapshot["casters"]
    result = session.query("spells.available", {"actor_id": current})
    ids = {row["spell_id"] for row in result["spells"]}
    assert {
        "spell:arc-lance",
        "spell:echo-burst",
        "spell:binding-haze",
        "spell:resonant-field",
        "spell:mending-light",
    }.issubset(ids)
    assert result["slots"] == [
        {"level": 1, "current": 3, "maximum": 3},
        {"level": 2, "current": 1, "maximum": 1},
    ]


def test_cantrip_attack_uses_action_but_no_spell_slot() -> None:
    session = _session()
    caster = session.encounter.current_actor_id
    assert caster is not None
    target = _other_actor(session, caster)
    before_slots = session.spell_state.caster(caster).slots

    preview = session.preview(
        "spells.preview",
        {
            "caster_id": caster,
            "spell_id": "spell:arc-lance",
            "slot_level": 0,
            "target_ids": [target],
        },
    )
    assert preview["legal"] is True
    result = session.handle_command(
        _command(
            session,
            caster,
            "tactical.cast_spell",
            {
                "spell_id": "spell:arc-lance",
                "slot_level": 0,
                "target_ids": [target],
            },
            1,
        )
    )
    assert result.presentation_events[0]["type"] == "tactical.spell_resolved"
    assert session.spell_state.caster(caster).slots == before_slots
    assert session.encounter.combatant(caster).economy.action_available is False


def test_upcast_healing_spends_requested_higher_slot() -> None:
    session = _session()
    caster = session.encounter.current_actor_id
    assert caster is not None

    result = session.handle_command(
        _command(
            session,
            caster,
            "tactical.cast_spell",
            {
                "spell_id": "spell:mending-light",
                "slot_level": 2,
                "target_ids": [],
            },
            1,
        )
    )
    assert result.result["spell_id"] == "spell:mending-light"
    assert session.spell_state.caster(caster).slot(2).current == 0
    assert session.spell_state.caster(caster).slot(1).current == 3


def test_save_area_preview_and_cast_use_authoritative_area_membership() -> None:
    session = _session(seed=11)
    caster = session.encounter.current_actor_id
    assert caster is not None
    target = _other_actor(session, caster)
    point = session.spatial.placement(target).anchor
    preview = session.preview(
        "spells.preview",
        {
            "caster_id": caster,
            "spell_id": "spell:echo-burst",
            "slot_level": 1,
            "target_ids": [],
            "point": {"x": point.x, "y": point.y},
        },
    )
    assert preview["legal"] is True
    assert target in preview["target_ids"]
    assert preview["area"]["cells"]

    session.handle_command(
        _command(
            session,
            caster,
            "tactical.cast_spell",
            {
                "spell_id": "spell:echo-burst",
                "slot_level": 1,
                "target_ids": [],
                "point": {"x": point.x, "y": point.y},
            },
            1,
        )
    )
    assert session.spell_state.caster(caster).slot(1).current == 2


def test_concentration_replaces_prior_concentration_and_duration_ticks() -> None:
    session = _session(seed=17)
    caster = session.encounter.current_actor_id
    assert caster is not None
    target = _other_actor(session, caster)
    point = session.spatial.placement(target).anchor

    session.handle_command(
        _command(
            session,
            caster,
            "tactical.cast_spell",
            {
                "spell_id": "spell:binding-haze",
                "slot_level": 1,
                "target_ids": [],
                "point": {"x": point.x, "y": point.y},
            },
            1,
        )
    )
    assert session.spell_state.caster(caster).concentration is not None
    assert session.spell_state.caster(caster).concentration.spell_id == "spell:binding-haze"

    index = _end_until_turn(session, caster, 2)
    point = session.spatial.placement(target).anchor
    session.handle_command(
        _command(
            session,
            caster,
            "tactical.cast_spell",
            {
                "spell_id": "spell:resonant-field",
                "slot_level": 1,
                "target_ids": [],
                "point": {"x": point.x, "y": point.y},
            },
            index,
        )
    )
    assert session.spell_state.caster(caster).concentration is not None
    assert session.spell_state.caster(caster).concentration.spell_id == "spell:resonant-field"
    assert all(
        effect.spell_id != "spell:binding-haze"
        for effect in session.spell_state.active_effects
    )


def test_v03_target_selector_filters_spell_candidates() -> None:
    session = _session()
    caster = session.encounter.current_actor_id
    assert caster is not None
    caster_tag = next(
        tag
        for tag in session.encounter.combatant(caster).actor.tags
        if tag.startswith("team:")
    )
    definition = SpellDefinition(
        spell_id="spell:selector-proof",
        name="Selector Proof",
        level=0,
        resolution=SpellResolution.AUTOMATIC,
        target_kind=SpellTargetKind.CREATURE,
        range_feet=100,
        requires_preparation=False,
        selector=TargetSelector(TargetMode.ALL, excluded_tags=frozenset({caster_tag})),
        effects=(SpellEffectSpec(SpellEffectKind.HEALING, flat_amount=1),),
    )
    session.spell_runtime.definitions[definition.spell_id] = definition
    state_caster = session.spell_state.caster(caster)
    from dataclasses import replace

    session.spell_state = session.spell_state.replace_caster(
        replace(
            state_caster,
            known_spell_ids=(*state_caster.known_spell_ids, definition.spell_id),
        )
    )
    target = _other_actor(session, caster)
    preview = session.spell_runtime.preview_cast(
        session.spell_state,
        session.encounter,
        session.spatial,
        caster_id=caster,
        spell_id=definition.spell_id,
        target_ids=(target,),
    )
    assert preview["legal"] is True
    self_preview = session.spell_runtime.preview_cast(
        session.spell_state,
        session.encounter,
        session.spatial,
        caster_id=caster,
        spell_id=definition.spell_id,
        target_ids=(caster,),
    )
    assert self_preview["legal"] is False


def test_spell_event_serialization_is_canonical_and_versioned() -> None:
    event = SpellEvent(
        sequence=1,
        event_type="spell.cast",
        caster_id="actor:ember",
        spell_id="spell:arc-lance",
        target_ids=("actor:shale",),
        payload=(("slot_level", 0),),
    )
    encoded = spell_event_to_dict(event)
    assert spell_event_from_dict(encoded) == event
    line = spell_events_jsonl((event,))
    assert json.loads(line)["event_type"] == "spell.cast"
    with pytest.raises(ValidationError):
        spell_events_jsonl((event, SpellEvent(3, "spell.cast", "actor:ember", "spell:arc-lance")))
