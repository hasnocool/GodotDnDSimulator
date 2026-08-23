# engine/src/godot_dnd_engine/world/content.py
"""Original v1.0 village-and-dungeon campaign fixture."""

from __future__ import annotations

from .model import (
    AreaDefinition,
    CampaignDefinition,
    DialogueChoice,
    DialogueDefinition,
    DialogueNode,
    EncounterGate,
    EquipmentCompatibility,
    InteractionDefinition,
    QuestDefinition,
    QuestStatus,
    ShopDefinition,
    ShopItem,
)


def demo_campaign() -> CampaignDefinition:
    """Return a compact original campaign exercising the v1.0 world loop."""

    return CampaignDefinition(
        campaign_id="campaign:lanterns-below",
        title="Lanterns Below",
        start_area_id="area:reedhollow-square",
        areas=(
            AreaDefinition(
                "area:reedhollow-square",
                "Reedhollow Square",
                exits=("area:old-road", "area:market-row"),
                tags=frozenset({"village", "safe-rest"}),
            ),
            AreaDefinition(
                "area:market-row",
                "Market Row",
                exits=("area:reedhollow-square",),
                tags=frozenset({"village", "shop"}),
            ),
            AreaDefinition(
                "area:old-road",
                "Old Quarry Road",
                exits=("area:reedhollow-square", "area:quarry-mouth"),
                tags=frozenset({"wilderness"}),
            ),
            AreaDefinition(
                "area:quarry-mouth",
                "Sunken Quarry Mouth",
                exits=("area:old-road", "area:underworks"),
                tags=frozenset({"dungeon-entry"}),
            ),
            AreaDefinition(
                "area:underworks",
                "Flooded Underworks",
                exits=("area:quarry-mouth", "area:lantern-vault"),
                tags=frozenset({"dungeon"}),
            ),
            AreaDefinition(
                "area:lantern-vault",
                "Lantern Vault",
                exits=("area:underworks",),
                tags=frozenset({"dungeon", "boss"}),
            ),
        ),
        dialogues=(
            DialogueDefinition(
                dialogue_id="dialogue:warden-ilar",
                area_id="area:reedhollow-square",
                start_node_id="node:warden-intro",
                nodes=(
                    DialogueNode(
                        "node:warden-intro",
                        "Warden Ilar",
                        (
                            "Three surveyors vanished below the quarry. "
                            "I need someone to learn what woke there."
                        ),
                        choices=(
                            DialogueChoice(
                                "choice:accept-quarry",
                                "We will investigate the quarry.",
                                next_node_id="node:warden-accepted",
                                set_flags=("flag:quarry-mission",),
                                quest_id="quest:lanterns-below",
                                quest_status=QuestStatus.ACTIVE,
                            ),
                            DialogueChoice(
                                "choice:decline-quarry",
                                "Not yet.",
                            ),
                        ),
                    ),
                    DialogueNode(
                        "node:warden-accepted",
                        "Warden Ilar",
                        (
                            "Take the old road. If you find the survey "
                            "lantern, bring it back—or use it to seal "
                            "the vault."
                        ),
                        choices=(
                            DialogueChoice(
                                "choice:leave-warden",
                                "We understand.",
                            ),
                        ),
                    ),
                ),
            ),
            DialogueDefinition(
                dialogue_id="dialogue:surveyor-echo",
                area_id="area:underworks",
                start_node_id="node:echo-choice",
                nodes=(
                    DialogueNode(
                        "node:echo-choice",
                        "Surveyor's Echo",
                        (
                            "A trapped echo offers to guide you if you "
                            "free it from the survey lantern."
                        ),
                        choices=(
                            DialogueChoice(
                                "choice:free-echo",
                                "Free the echo and trust its route.",
                                required_flags=frozenset(
                                    {"flag:survey-lantern-found"}
                                ),
                                set_flags=(
                                    "flag:echo-freed",
                                    "flag:vault-route-known",
                                ),
                            ),
                            DialogueChoice(
                                "choice:keep-lantern",
                                "Keep the lantern intact for the seal.",
                                required_flags=frozenset(
                                    {"flag:survey-lantern-found"}
                                ),
                                set_flags=("flag:lantern-kept",),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        quests=(
            QuestDefinition(
                "quest:lanterns-below",
                "Lanterns Below",
                (
                    "Investigate the quarry, learn what happened to the "
                    "surveyors, and decide the fate of the lantern vault."
                ),
                start_status=QuestStatus.AVAILABLE,
            ),
        ),
        shops=(
            ShopDefinition(
                "shop:reedhollow-supplies",
                "area:market-row",
                "Reedhollow Supplies",
                items=(
                    ShopItem(
                        "item:healing-draught",
                        buy_price=8,
                        sell_price=3,
                        stock=4,
                    ),
                    ShopItem(
                        "item:rope-coil",
                        buy_price=5,
                        sell_price=2,
                        stock=3,
                    ),
                    ShopItem(
                        "item:quarry-lantern",
                        buy_price=10,
                        sell_price=4,
                        stock=1,
                    ),
                ),
            ),
        ),
        interactions=(
            InteractionDefinition(
                "interaction:collapsed-marker",
                "area:old-road",
                "Read the collapsed survey marker",
                dc=11,
                ability="intelligence",
                success_flags=("flag:marker-deciphered",),
                reward_currency=3,
            ),
            InteractionDefinition(
                "interaction:flooded-gate",
                "area:quarry-mouth",
                "Cross the flooded gate",
                dc=12,
                ability="strength",
                success_flags=("flag:flooded-gate-open",),
                failure_flags=("flag:flooded-gate-failed",),
            ),
            InteractionDefinition(
                "interaction:survey-lantern",
                "area:underworks",
                "Recover the survey lantern",
                dc=10,
                ability="wisdom",
                success_flags=("flag:survey-lantern-found",),
                reward_item_id="item:survey-lantern",
            ),
            InteractionDefinition(
                "interaction:stonefall-trigger",
                "area:underworks",
                "Disarm the suspended stonefall trigger",
                dc=13,
                ability="dexterity",
                success_flags=("flag:stonefall-disarmed",),
                failure_flags=("flag:stonefall-triggered",),
            ),
        ),
        encounters=(
            EncounterGate(
                "encounter:road-ambush",
                "area:old-road",
                "Roadside Scavengers",
                required_flags=frozenset({"flag:quarry-mission"}),
                completion_flags=("flag:road-cleared",),
            ),
            EncounterGate(
                "encounter:quarry-watchers",
                "area:quarry-mouth",
                "Quarry Watchers",
                required_flags=frozenset({"flag:road-cleared"}),
                completion_flags=("flag:quarry-cleared",),
            ),
            EncounterGate(
                "encounter:underworks-swarm",
                "area:underworks",
                "Underworks Swarm",
                required_flags=frozenset({"flag:quarry-cleared"}),
                completion_flags=("flag:underworks-cleared",),
            ),
            EncounterGate(
                "encounter:vault-warden",
                "area:lantern-vault",
                "The Hollow Warden",
                required_flags=frozenset({"flag:underworks-cleared"}),
                completion_flags=(
                    "flag:vault-warden-defeated",
                    "flag:campaign-complete",
                ),
                boss=True,
            ),
        ),
        equipment_compatibility=(
            EquipmentCompatibility(
                "item:healing-draught",
                ("slot:consumable",),
            ),
            EquipmentCompatibility(
                "item:rope-coil",
                ("slot:utility",),
            ),
            EquipmentCompatibility(
                "item:quarry-lantern",
                ("slot:utility",),
            ),
            EquipmentCompatibility(
                "item:survey-lantern",
                ("slot:utility",),
            ),
        ),
    )
