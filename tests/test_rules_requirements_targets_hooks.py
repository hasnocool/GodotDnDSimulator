from __future__ import annotations

from godot_dnd_engine.rules import (
    ConditionInstance,
    ReactionHook,
    Requirement,
    RequirementKind,
    ResourcePool,
    RuleEventView,
    RuleSubjectState,
    RuleWorldState,
    RulesetCapabilities,
    TargetMode,
    TargetSelector,
    Trigger,
    collect_reactions,
    evaluate_requirements,
    select_targets,
)


def _world() -> RuleWorldState:
    return RuleWorldState(
        (
            RuleSubjectState(
                "actor:a",
                tags=frozenset({"ally", "awake"}),
                resources=(ResourcePool("resource:reaction", 1, 1),),
                conditions=(ConditionInstance("condition:guarding"),),
            ),
            RuleSubjectState("actor:b", tags=frozenset({"ally", "awake"})),
            RuleSubjectState("actor:c", tags=frozenset({"enemy", "awake"})),
        )
    )


def test_requirement_model_covers_tags_resources_conditions_and_capabilities() -> None:
    capabilities = RulesetCapabilities.srd_5_2_1_core()
    subject = _world().subject("actor:a")
    requirements = (
        Requirement("requirement:tag", RequirementKind.TAG_PRESENT, "awake"),
        Requirement("requirement:not-tag", RequirementKind.TAG_ABSENT, "unconscious"),
        Requirement(
            "requirement:resource",
            RequirementKind.RESOURCE_AT_LEAST,
            "resource:reaction",
            minimum=1,
        ),
        Requirement(
            "requirement:condition",
            RequirementKind.CONDITION_PRESENT,
            "condition:guarding",
        ),
        Requirement(
            "requirement:not-condition",
            RequirementKind.CONDITION_ABSENT,
            "condition:stunned",
        ),
        Requirement("requirement:capability", RequirementKind.CAPABILITY, "reactions"),
    )
    assert evaluate_requirements(requirements, subject, capabilities).passed

    failed = evaluate_requirements(
        (Requirement("requirement:missing", RequirementKind.TAG_PRESENT, "missing"),),
        subject,
        capabilities,
    )
    assert failed.failed_requirement_ids == ("requirement:missing",)


def test_target_selection_is_deterministic_and_presentation_independent() -> None:
    world = _world()
    selector = TargetSelector(
        TargetMode.ALL,
        required_tags=frozenset({"awake"}),
        excluded_tags=frozenset({"enemy"}),
    )
    selected = select_targets(selector, world, source_id="actor:a")
    assert [subject.subject_id for subject in selected] == ["actor:b"]
    single = TargetSelector(TargetMode.SINGLE, required_tags=frozenset({"awake"}))
    assert select_targets(single, world, source_id="actor:a")[0].subject_id == "actor:b"
    self_selector = TargetSelector(TargetMode.SELF, required_tags=frozenset({"ally"}))
    assert select_targets(self_selector, world, source_id="actor:a")[0].subject_id == "actor:a"


def test_reaction_hooks_match_trigger_requirements_and_priority() -> None:
    world = _world()
    capabilities = RulesetCapabilities.srd_5_2_1_core()
    event = RuleEventView("event:test", actor_id="actor:c", tags=frozenset({"hostile"}))
    hooks = (
        ReactionHook(
            "hook:later",
            "actor:a",
            Trigger("event:test", frozenset({"hostile"})),
            requirements=(
                Requirement(
                    "requirement:reaction",
                    RequirementKind.RESOURCE_AT_LEAST,
                    "resource:reaction",
                    minimum=1,
                ),
            ),
            priority=20,
        ),
        ReactionHook(
            "hook:first",
            "actor:a",
            Trigger("event:test", frozenset({"hostile"})),
            priority=10,
        ),
        ReactionHook("hook:no-match", "actor:a", Trigger("event:other"), priority=0),
    )
    matches = collect_reactions(event, hooks, world, capabilities)
    assert [match.hook.hook_id for match in matches] == ["hook:first", "hook:later"]
