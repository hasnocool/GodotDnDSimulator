# engine/src/godot_dnd_engine/rules/capabilities.py
"""Ruleset capability declarations used to gate generic runtime features."""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import ValidationError

CORE_V03_CAPABILITIES = frozenset(
    {
        "d20_tests",
        "advantage_disadvantage",
        "modifier_pipeline",
        "resources",
        "requirements",
        "target_selectors",
        "effects",
        "durations",
        "conditions",
        "reactions",
    }
)


@dataclass(frozen=True, slots=True)
class RulesetCapabilities:
    ruleset_id: str
    ruleset_version: str
    supported: frozenset[str]

    def __post_init__(self) -> None:
        if not isinstance(self.ruleset_id, str) or not self.ruleset_id.strip():
            raise ValidationError("ruleset_id must be a non-empty string")
        if not isinstance(self.ruleset_version, str) or not self.ruleset_version.strip():
            raise ValidationError("ruleset_version must be a non-empty string")
        if any(not isinstance(item, str) or not item for item in self.supported):
            raise ValidationError("capability names must be non-empty strings")

    def supports(self, capability: str) -> bool:
        return capability in self.supported

    def require(self, *capabilities: str) -> None:
        missing = sorted(item for item in capabilities if item not in self.supported)
        if missing:
            raise ValidationError(f"ruleset lacks required capabilities: {', '.join(missing)}")

    @classmethod
    def srd_5_2_1_core(cls) -> RulesetCapabilities:
        return cls(
            ruleset_id="wotc-srd-5.2.1-en",
            ruleset_version="5.2.1",
            supported=CORE_V03_CAPABILITIES,
        )
