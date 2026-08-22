# scripts/determinism_smoke.py
"""Run the v0.1 deterministic command -> event -> state smoke scenario."""

from __future__ import annotations

from godot_dnd_engine.engine import SimulationEngine
from godot_dnd_engine.models import CommandEnvelope
from godot_dnd_engine.serialization import dumps_canonical, event_to_dict, state_to_dict


def run_once() -> tuple[str, str]:
    engine = SimulationEngine.create(
        campaign_id="campaign:smoke",
        session_id="session:smoke",
        seed=20260821,
    )
    event = engine.handle(
        CommandEnvelope(
            command_id="command:smoke-roll",
            campaign_id="campaign:smoke",
            session_id="session:smoke",
            actor_id="actor:smoke-hero",
            command_type="simulation.roll_dice",
            expected_sequence=0,
            payload={
                "expression": "1d20+4",
                "counter": "smoke_check",
                "reason": "v0.1 CI determinism smoke test",
            },
        )
    )[0]
    return dumps_canonical(event_to_dict(event)), dumps_canonical(state_to_dict(engine.state))


def main() -> int:
    first = run_once()
    second = run_once()
    if first != second:
        raise RuntimeError("determinism smoke test produced divergent results")
    print(first[0])
    print(first[1])
    print("Determinism smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
