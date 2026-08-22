# engine/src/godot_dnd_engine/world/runtime.py
"""Deterministic event-sourced v1.0 campaign/world runtime."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from ..errors import SequenceError, UnsupportedCommandError, ValidationError
from ..rng import DeterministicRNG
from .model import (
    CampaignDefinition,
    DialogueChoice,
    DialogueDefinition,
    EncounterGate,
    InteractionDefinition,
    QuestStatus,
    ShopDefinition,
    WorldEvent,
    WorldState,
)


class WorldRuntime:
    def __init__(self, definition: CampaignDefinition, *, seed: int) -> None:
        self.definition = definition
        self.rng = DeterministicRNG.from_seed(seed)
        self.state = WorldState(
            sequence=0,
            current_area_id=definition.start_area_id,
            party_ids=(),
            flags=frozenset(),
            quests=tuple((item.quest_id, item.start_status) for item in definition.quests),
            inventory=(),
            equipped=(),
            currency=25,
            active_dialogue=None,
            completed_encounters=frozenset(),
            journal=(f"Arrived in {definition.title}.",),
            rest_count=0,
        )
        self.events: list[WorldEvent] = []
        self._areas = {item.area_id: item for item in definition.areas}
        self._dialogues = {item.dialogue_id: item for item in definition.dialogues}
        self._shops = {item.shop_id: item for item in definition.shops}
        self._interactions = {item.interaction_id: item for item in definition.interactions}
        self._encounters = {item.encounter_id: item for item in definition.encounters}

    def snapshot(self) -> dict[str, object]:
        rng_state, rng_increment = self.rng.snapshot()
        return {
            "schema_version": 1,
            "state": self.state_to_dict(),
            "rng": {
                "algorithm": self.rng.ALGORITHM,
                "state": rng_state,
                "increment": rng_increment,
            },
            "events": [event_to_dict(item) for item in self.events],
        }

    def state_to_dict(self) -> dict[str, object]:
        area = self._areas[self.state.current_area_id]
        return {
            "campaign_id": self.definition.campaign_id,
            "sequence": self.state.sequence,
            "mode": "world",
            "area": {"area_id": area.area_id, "name": area.name, "tags": sorted(area.tags)},
            "party_ids": list(self.state.party_ids),
            "flags": sorted(self.state.flags),
            "quests": {key: value.value for key, value in self.state.quests},
            "inventory": dict(self.state.inventory),
            "equipped": dict(self.state.equipped),
            "currency": self.state.currency,
            "active_dialogue": None
            if self.state.active_dialogue is None
            else {
                "dialogue_id": self.state.active_dialogue[0],
                "node_id": self.state.active_dialogue[1],
            },
            "completed_encounters": sorted(self.state.completed_encounters),
            "journal": list(self.state.journal),
            "rest_count": self.state.rest_count,
        }

    def query(self, query_type: str, payload: Mapping[str, Any]) -> dict[str, object]:
        if query_type == "world.snapshot":
            return {"snapshot": self.snapshot()}
        if query_type == "world.actions":
            return self._actions()
        if query_type == "world.map":
            return {
                "current_area_id": self.state.current_area_id,
                "areas": [
                    {
                        "area_id": item.area_id,
                        "name": item.name,
                        "exits": list(item.exits),
                        "visited": item.area_id == self.state.current_area_id
                        or f"visited:{item.area_id}" in self.state.flags,
                    }
                    for item in self.definition.areas
                ],
            }
        if query_type == "world.journal":
            return {
                "quests": {key: value.value for key, value in self.state.quests},
                "entries": list(self.state.journal),
            }
        if query_type == "world.party":
            return {"party_ids": list(self.state.party_ids), "equipped": dict(self.state.equipped)}
        if query_type == "dialogue.current":
            return self._dialogue_view()
        if query_type == "shop.inventory":
            shop_id = _string(payload.get("shop_id"), "shop_id")
            return self._shop_view(self._shop(shop_id))
        raise UnsupportedCommandError(f"unsupported world query: {query_type}")

    def handle_command(
        self,
        command_type: str,
        payload: Mapping[str, Any],
        *,
        expected_sequence: int | None,
    ) -> dict[str, object]:
        if expected_sequence is not None and expected_sequence != self.state.sequence:
            raise SequenceError(
                f"expected world sequence {expected_sequence}, current {self.state.sequence}"
            )
        if command_type == "world.start":
            events = self._start(payload)
        elif command_type == "world.travel":
            events = self._travel(payload)
        elif command_type == "dialogue.start":
            events = self._dialogue_start(payload)
        elif command_type == "dialogue.choose":
            events = self._dialogue_choose(payload)
        elif command_type == "world.resolve_interaction":
            events = self._resolve_interaction(payload)
        elif command_type == "shop.buy":
            events = self._buy(payload)
        elif command_type == "shop.sell":
            events = self._sell(payload)
        elif command_type == "inventory.equip":
            events = self._equip(payload)
        elif command_type == "world.rest":
            events = self._rest()
        elif command_type == "world.complete_encounter":
            events = self._complete_encounter(payload)
        else:
            raise UnsupportedCommandError(f"unsupported world command: {command_type}")
        for event in events:
            self.state = apply_world_event(self.state, event)
            self.events.append(event)
        return {
            "snapshot": self.snapshot(),
            "events": [event_to_dict(item) for item in events],
            "presentation_events": [self._presentation_event(item) for item in events],
        }

    def _emit(
        self,
        event_type: str,
        payload: Mapping[str, object],
        *,
        rng_after: tuple[int, int] | None = None,
        offset: int = 1,
    ) -> WorldEvent:
        return WorldEvent(
            sequence=self.state.sequence + offset,
            event_type=event_type,
            payload=tuple(sorted(payload.items())),
            rng_after=rng_after,
        )

    def _start(self, payload: Mapping[str, Any]) -> tuple[WorldEvent, ...]:
        if self.state.party_ids:
            raise ValidationError("campaign already has a party")
        party = _string_tuple(payload.get("party_ids", []), "party_ids")
        if not 1 <= len(party) <= 6 or len(party) != len(set(party)):
            raise ValidationError("party must contain 1..6 unique actor IDs")
        return (
            self._emit(
                "world.started",
                {
                    "party_ids": list(party),
                    "area_id": self.definition.start_area_id,
                    "journal_entry": "The party begins its journey.",
                },
            ),
        )

    def _travel(self, payload: Mapping[str, Any]) -> tuple[WorldEvent, ...]:
        destination = _string(payload.get("area_id"), "area_id")
        area = self._areas[self.state.current_area_id]
        if destination not in area.exits:
            raise ValidationError("destination is not connected to current area")
        if self.state.active_dialogue is not None:
            raise ValidationError("cannot travel during active dialogue")
        if destination not in self._areas:
            raise ValidationError("unknown destination area")
        return (
            self._emit(
                "world.travelled",
                {
                    "area_id": destination,
                    "visited_flag": f"visited:{destination}",
                    "journal_entry": f"Travelled to {self._areas[destination].name}.",
                },
            ),
        )

    def _dialogue_start(self, payload: Mapping[str, Any]) -> tuple[WorldEvent, ...]:
        dialogue_id = _string(payload.get("dialogue_id"), "dialogue_id")
        dialogue = self._dialogue(dialogue_id)
        return (
            self._emit(
                "dialogue.started",
                {"dialogue_id": dialogue_id, "node_id": dialogue.start_node_id},
            ),
        )

    def _dialogue_choose(self, payload: Mapping[str, Any]) -> tuple[WorldEvent, ...]:
        if self.state.active_dialogue is None:
            raise ValidationError("no active dialogue")
        dialogue_id, node_id = self.state.active_dialogue
        dialogue = self._dialogue(dialogue_id)
        node = next(item for item in dialogue.nodes if item.node_id == node_id)
        choice_id = _string(payload.get("choice_id"), "choice_id")
        choice = next((item for item in node.choices if item.choice_id == choice_id), None)
        if choice is None or not self._choice_available(choice):
            raise ValidationError("dialogue choice is not available")
        next_node = choice.next_node_id
        event_payload: dict[str, object] = {
            "dialogue_id": dialogue_id,
            "choice_id": choice.choice_id,
            "next_node_id": next_node,
            "set_flags": list(choice.set_flags),
            "clear_flags": list(choice.clear_flags),
            "journal_entry": f"Dialogue choice: {choice.text}",
        }
        if choice.quest_id is not None and choice.quest_status is not None:
            event_payload["quest_id"] = choice.quest_id
            event_payload["quest_status"] = choice.quest_status.value
        return (self._emit("dialogue.choice_resolved", event_payload),)

    def _resolve_interaction(self, payload: Mapping[str, Any]) -> tuple[WorldEvent, ...]:
        interaction_id = _string(payload.get("interaction_id"), "interaction_id")
        bonus = _integer(payload.get("bonus", 0), "bonus")
        interaction = self._interaction(interaction_id)
        self._require_here(interaction.area_id)
        roll = self.rng.roll_die(20)
        total = roll + bonus
        success = total >= interaction.dc
        event_payload: dict[str, object] = {
            "interaction_id": interaction.interaction_id,
            "ability": interaction.ability,
            "roll": roll,
            "bonus": bonus,
            "total": total,
            "dc": interaction.dc,
            "success": success,
            "set_flags": list(interaction.success_flags if success else interaction.failure_flags),
            "journal_entry": f"{interaction.name}: {'success' if success else 'failure'} ({total} vs {interaction.dc}).",
        }
        if success and interaction.reward_item_id is not None:
            event_payload["reward_item_id"] = interaction.reward_item_id
        if success and interaction.reward_currency:
            event_payload["reward_currency"] = interaction.reward_currency
        return (
            self._emit(
                "world.interaction_resolved",
                event_payload,
                rng_after=self.rng.snapshot(),
            ),
        )

    def _buy(self, payload: Mapping[str, Any]) -> tuple[WorldEvent, ...]:
        shop = self._shop(_string(payload.get("shop_id"), "shop_id"))
        self._require_here(shop.area_id)
        item_id = _string(payload.get("item_id"), "item_id")
        quantity = _positive_integer(payload.get("quantity", 1), "quantity")
        item = next((row for row in shop.items if row.item_id == item_id), None)
        if item is None:
            raise ValidationError("item is not sold by this shop")
        if item.stock is not None and quantity > item.stock:
            raise ValidationError("requested quantity exceeds shop stock")
        cost = item.buy_price * quantity
        if cost > self.state.currency:
            raise ValidationError("not enough currency")
        return (
            self._emit(
                "shop.bought",
                {"shop_id": shop.shop_id, "item_id": item_id, "quantity": quantity, "currency_delta": -cost},
            ),
        )

    def _sell(self, payload: Mapping[str, Any]) -> tuple[WorldEvent, ...]:
        shop = self._shop(_string(payload.get("shop_id"), "shop_id"))
        self._require_here(shop.area_id)
        item_id = _string(payload.get("item_id"), "item_id")
        quantity = _positive_integer(payload.get("quantity", 1), "quantity")
        item = next((row for row in shop.items if row.item_id == item_id), None)
        if item is None:
            raise ValidationError("shop does not trade this item")
        if dict(self.state.inventory).get(item_id, 0) < quantity:
            raise ValidationError("party does not own requested quantity")
        return (
            self._emit(
                "shop.sold",
                {
                    "shop_id": shop.shop_id,
                    "item_id": item_id,
                    "quantity": quantity,
                    "currency_delta": item.sell_price * quantity,
                },
            ),
        )

    def _equip(self, payload: Mapping[str, Any]) -> tuple[WorldEvent, ...]:
        actor_id = _string(payload.get("actor_id"), "actor_id")
        slot = _string(payload.get("slot"), "slot")
        item_id = _string(payload.get("item_id"), "item_id")
        if actor_id not in self.state.party_ids:
            raise ValidationError("actor is not in the active party")
        if dict(self.state.inventory).get(item_id, 0) < 1:
            raise ValidationError("party does not own item")
        return (self._emit("inventory.equipped", {"actor_id": actor_id, "slot": slot, "item_id": item_id}),)

    def _rest(self) -> tuple[WorldEvent, ...]:
        if self.state.active_dialogue is not None:
            raise ValidationError("cannot rest during active dialogue")
        return (
            self._emit(
                "world.rested",
                {"rest_count": self.state.rest_count + 1, "journal_entry": "The party rested."},
            ),
        )

    def _complete_encounter(self, payload: Mapping[str, Any]) -> tuple[WorldEvent, ...]:
        encounter_id = _string(payload.get("encounter_id"), "encounter_id")
        gate = self._encounter(encounter_id)
        self._require_here(gate.area_id)
        if encounter_id in self.state.completed_encounters:
            raise ValidationError("encounter is already complete")
        if not gate.required_flags.issubset(self.state.flags):
            raise ValidationError("encounter prerequisites are not satisfied")
        return (
            self._emit(
                "world.encounter_completed",
                {
                    "encounter_id": encounter_id,
                    "boss": gate.boss,
                    "set_flags": list(gate.completion_flags),
                    "journal_entry": f"Encounter completed: {gate.name}.",
                },
            ),
        )

    def _actions(self) -> dict[str, object]:
        area_id = self.state.current_area_id
        area = self._areas[area_id]
        return {
            "area_id": area_id,
            "travel": [{"area_id": item, "name": self._areas[item].name} for item in area.exits],
            "shops": [self._shop_view(item) for item in self.definition.shops if item.area_id == area_id],
            "interactions": [
                {"interaction_id": item.interaction_id, "name": item.name, "ability": item.ability, "dc": item.dc}
                for item in self.definition.interactions
                if item.area_id == area_id
            ],
            "encounters": [
                {
                    "encounter_id": item.encounter_id,
                    "name": item.name,
                    "boss": item.boss,
                    "available": item.required_flags.issubset(self.state.flags)
                    and item.encounter_id not in self.state.completed_encounters,
                }
                for item in self.definition.encounters
                if item.area_id == area_id
            ],
            "can_rest": self.state.active_dialogue is None,
        }

    def _dialogue_view(self) -> dict[str, object]:
        if self.state.active_dialogue is None:
            return {"active": False}
        dialogue_id, node_id = self.state.active_dialogue
        dialogue = self._dialogue(dialogue_id)
        node = next(item for item in dialogue.nodes if item.node_id == node_id)
        return {
            "active": True,
            "dialogue_id": dialogue_id,
            "node_id": node_id,
            "speaker": node.speaker,
            "text": node.text,
            "choices": [
                {"choice_id": choice.choice_id, "text": choice.text}
                for choice in node.choices
                if self._choice_available(choice)
            ],
        }

    def _choice_available(self, choice: DialogueChoice) -> bool:
        return choice.required_flags.issubset(self.state.flags) and not choice.forbidden_flags.intersection(self.state.flags)

    def _shop_view(self, shop: ShopDefinition) -> dict[str, object]:
        return {
            "shop_id": shop.shop_id,
            "name": shop.name,
            "area_id": shop.area_id,
            "items": [
                {
                    "item_id": item.item_id,
                    "buy_price": item.buy_price,
                    "sell_price": item.sell_price,
                    "stock": item.stock,
                }
                for item in shop.items
            ],
        }

    def _dialogue(self, dialogue_id: str) -> DialogueDefinition:
        value = self._dialogues.get(dialogue_id)
        if value is None:
            raise ValidationError("unknown dialogue")
        return value

    def _shop(self, shop_id: str) -> ShopDefinition:
        value = self._shops.get(shop_id)
        if value is None:
            raise ValidationError("unknown shop")
        return value

    def _interaction(self, interaction_id: str) -> InteractionDefinition:
        value = self._interactions.get(interaction_id)
        if value is None:
            raise ValidationError("unknown interaction")
        return value

    def _encounter(self, encounter_id: str) -> EncounterGate:
        value = self._encounters.get(encounter_id)
        if value is None:
            raise ValidationError("unknown encounter")
        return value

    def _require_here(self, area_id: str) -> None:
        if area_id != self.state.current_area_id:
            raise ValidationError("content is not available in current area")

    @staticmethod
    def _presentation_event(event: WorldEvent) -> dict[str, object]:
        return {
            "sequence": event.sequence,
            "type": event.event_type,
            "payload": dict(event.payload),
        }


def apply_world_event(state: WorldState, event: WorldEvent) -> WorldState:
    if event.sequence != state.sequence + 1:
        raise SequenceError("world event sequence is not contiguous")
    payload = dict(event.payload)
    flags = set(state.flags)
    quests = dict(state.quests)
    inventory = dict(state.inventory)
    equipped = dict(state.equipped)
    journal = list(state.journal)
    party_ids = state.party_ids
    area_id = state.current_area_id
    active_dialogue = state.active_dialogue
    completed = set(state.completed_encounters)
    currency = state.currency
    rest_count = state.rest_count

    if event.event_type == "world.started":
        party_ids = tuple(str(item) for item in payload["party_ids"])
        area_id = str(payload["area_id"])
    elif event.event_type == "world.travelled":
        area_id = str(payload["area_id"])
        flags.add(str(payload["visited_flag"]))
    elif event.event_type == "dialogue.started":
        active_dialogue = (str(payload["dialogue_id"]), str(payload["node_id"]))
    elif event.event_type == "dialogue.choice_resolved":
        for item in payload.get("set_flags", []):
            flags.add(str(item))
        for item in payload.get("clear_flags", []):
            flags.discard(str(item))
        quest_id = payload.get("quest_id")
        quest_status = payload.get("quest_status")
        if quest_id is not None and quest_status is not None:
            quests[str(quest_id)] = QuestStatus(str(quest_status))
        next_node = payload.get("next_node_id")
        active_dialogue = None if next_node is None else (str(payload["dialogue_id"]), str(next_node))
    elif event.event_type == "world.interaction_resolved":
        for item in payload.get("set_flags", []):
            flags.add(str(item))
        reward_item = payload.get("reward_item_id")
        if reward_item is not None:
            key = str(reward_item)
            inventory[key] = inventory.get(key, 0) + 1
        currency += int(payload.get("reward_currency", 0))
    elif event.event_type in {"shop.bought", "shop.sold"}:
        item_id = str(payload["item_id"])
        quantity = int(payload["quantity"])
        delta = quantity if event.event_type == "shop.bought" else -quantity
        inventory[item_id] = inventory.get(item_id, 0) + delta
        if inventory[item_id] <= 0:
            inventory.pop(item_id, None)
        currency += int(payload["currency_delta"])
    elif event.event_type == "inventory.equipped":
        equipped[f"{payload['actor_id']}|{payload['slot']}"] = str(payload["item_id"])
    elif event.event_type == "world.rested":
        rest_count = int(payload["rest_count"])
    elif event.event_type == "world.encounter_completed":
        encounter_id = str(payload["encounter_id"])
        completed.add(encounter_id)
        for item in payload.get("set_flags", []):
            flags.add(str(item))
    else:
        raise UnsupportedCommandError(f"unsupported world event: {event.event_type}")

    entry = payload.get("journal_entry")
    if entry is not None:
        journal.append(str(entry))
    return replace(
        state,
        sequence=event.sequence,
        current_area_id=area_id,
        party_ids=party_ids,
        flags=frozenset(flags),
        quests=tuple(sorted(quests.items())),
        inventory=tuple(sorted(inventory.items())),
        equipped=tuple(sorted(equipped.items())),
        currency=currency,
        active_dialogue=active_dialogue,
        completed_encounters=frozenset(completed),
        journal=tuple(journal),
        rest_count=rest_count,
    )


def event_to_dict(event: WorldEvent) -> dict[str, object]:
    return {
        "sequence": event.sequence,
        "type": event.event_type,
        "payload": dict(event.payload),
        "rng_after": None
        if event.rng_after is None
        else {"state": event.rng_after[0], "increment": event.rng_after[1]},
    }


def replay_world_events(initial: WorldState, events: tuple[WorldEvent, ...]) -> WorldState:
    state = initial
    for event in events:
        state = apply_world_event(state, event)
    return state


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{label} must be a non-empty string")
    return value.strip()


def _string_tuple(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValidationError(f"{label} must be an array")
    result = tuple(_string(item, label) for item in value)
    return result


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{label} must be an integer")
    return value


def _positive_integer(value: object, label: str) -> int:
    result = _integer(value, label)
    if result < 1:
        raise ValidationError(f"{label} must be >= 1")
    return result
