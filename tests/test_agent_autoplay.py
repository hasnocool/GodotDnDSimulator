from __future__ import annotations

from godot_dnd_engine.agent_autoplay import run_lanterns_below_autoplay


def test_baseline_agents_complete_lanterns_below_end_to_end() -> None:
    result = run_lanterns_below_autoplay(seed=23, max_steps=2_000)

    assert result.completed, result.reason
    world = result.final_observation["world"]
    assert isinstance(world, dict)
    assert "flag:campaign-complete" in world["flags"]
    assert world["completed_encounters"] == [
        "encounter:quarry-watchers",
        "encounter:road-ambush",
        "encounter:underworks-swarm",
        "encounter:vault-warden",
    ]
    command_types = [step.command_type for step in result.steps]
    assert "world.start" in command_types
    assert "dialogue.choose" in command_types
    assert "shop.buy" in command_types
    assert "shop.sell" in command_types
    assert "world.resolve_interaction" in command_types
    assert "world.begin_encounter" in command_types
    assert "tactical.cast_spell" in command_types or "tactical.attack" in command_types
    assert "tactical.end_turn" in command_types
    assert command_types.count("world.complete_encounter") == 4


def test_autoplay_trace_is_deterministic_for_same_seed() -> None:
    first = run_lanterns_below_autoplay(seed=29, max_steps=2_000)
    second = run_lanterns_below_autoplay(seed=29, max_steps=2_000)

    assert first.completed and second.completed
    assert [step.to_dict() for step in first.steps] == [
        step.to_dict() for step in second.steps
    ]
    assert first.final_observation == second.final_observation
