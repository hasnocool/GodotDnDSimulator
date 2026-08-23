from __future__ import annotations

import pytest

from godot_dnd_engine.agent_api import AgentControlMode
from godot_dnd_engine.agent_autoplay import create_autoplay_session
from godot_dnd_engine.errors import ValidationError


def _action(
    observation: dict[str, object],
    command_type: str,
) -> dict[str, object]:
    value = observation.get("legal_actions", [])
    assert isinstance(value, list)
    return next(
        row
        for row in value
        if isinstance(row, dict) and row.get("command_type") == command_type
    )


def test_agent_observation_exposes_only_legal_action_tokens() -> None:
    session = create_autoplay_session(seed=13)
    observation = session.agent.observe()

    assert observation["context"] == "world"
    start = _action(observation, "world.start")
    assert str(start["action_id"]).startswith("agent-action:0:")
    assert start["payload"] == {
        "party_ids": [
            "actor:premade-aster",
            "actor:premade-mira",
            "actor:premade-sable",
            "actor:premade-tovan",
        ]
    }
    assert "world.start" not in str(observation["world"])


def test_agent_can_control_hero_and_stale_action_tokens_are_rejected() -> None:
    session = create_autoplay_session(seed=17)
    session.agent.controllers.set_control(
        "actor:premade-mira",
        AgentControlMode.AGENT,
        policy_id="test-policy",
    )
    initial = session.agent.observe()
    start = _action(initial, "world.start")
    session.agent.execute(str(start["action_id"]))

    controller = session.agent.controllers.controller_for(
        "actor:premade-mira",
        party_ids=session.world.state.party_ids,
    )
    assert controller.mode is AgentControlMode.AGENT
    assert controller.policy_id == "test-policy"

    current = session.agent.observe()
    travel = _action(current, "world.travel")
    rest = _action(current, "world.rest")
    session.agent.execute(str(rest["action_id"]))

    with pytest.raises(ValidationError, match="stale, unknown, or no longer legal"):
        session.agent.execute(str(travel["action_id"]))


def test_agent_execute_requires_explicit_agent_control_for_party_actor() -> None:
    session = create_autoplay_session(seed=19)
    start = _action(session.agent.observe(), "world.start")
    session.agent.execute(str(start["action_id"]))

    session.world.handle_command(
        "world.travel",
        {"area_id": "area:old-road"},
        expected_sequence=session.world.state.sequence,
    )
    interaction = next(
        row
        for row in session.agent.observe()["legal_actions"]
        if isinstance(row, dict)
        and row.get("command_type") == "world.resolve_interaction"
        and row.get("actor_id") == "actor:premade-mira"
    )
    with pytest.raises(ValidationError, match="human-controlled"):
        session.agent.execute(str(interaction["action_id"]))

    session.agent.controllers.set_control(
        "actor:premade-mira",
        AgentControlMode.AGENT,
        policy_id="test-policy",
    )
    refreshed = next(
        row
        for row in session.agent.observe()["legal_actions"]
        if isinstance(row, dict)
        and row.get("command_type") == "world.resolve_interaction"
        and row.get("actor_id") == "actor:premade-mira"
    )
    result = session.agent.execute(str(refreshed["action_id"]))
    assert result["executed_action"]["actor_id"] == "actor:premade-mira"
