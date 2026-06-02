import asyncio
import random
from dataclasses import dataclass
from typing import Any, Protocol

from apps.poker_engine.engine import apply_action, legal_actions
from apps.poker_engine.evaluator import RANK_VALUE
from apps.poker_engine.llm import LLMProviderUnavailable, PokerLLMProvider, validate_llm_decision

BEGINNER_POOL = ["fish", "fish", "fish", "tight"]
MEDIUM_POOL = ["fish", "tight", "tag", "pro_tag"]
ADVANCED_POOL = ["pro_tag", "pro_lag", "pro_exploit", "pro_balanced"]
BOT_PERSONALITY_POOLS = {
    "beginner": BEGINNER_POOL,
    "medium": MEDIUM_POOL,
    "advanced": ADVANCED_POOL,
}

HERO_SEAT = 0


class BotStrategy(Protocol):
    def choose_action(self, state: dict, seat_id: int) -> dict:
        pass


@dataclass(frozen=True)
class RandomBot:
    def choose_action(self, state: dict, seat_id: int) -> dict:
        actions = legal_actions(state)
        chosen = _bot_rng(state, seat_id).choice(actions)
        if "amount" in chosen:
            return {"action": chosen["action"], "amount": chosen["amount"]}
        if "min_amount" in chosen:
            return {"action": chosen["action"], "amount": chosen["min_amount"]}
        return {"action": chosen["action"]}


@dataclass(frozen=True)
class RuleBasedFish:
    def choose_action(self, state: dict, seat_id: int) -> dict:
        actions = _actions_by_name(state)
        if "check" in actions:
            return {"action": "check"}
        if "call" in actions:
            return {"action": "call"}
        return {"action": "fold"}


@dataclass(frozen=True)
class RuleBasedTight:
    def choose_action(self, state: dict, seat_id: int) -> dict:
        actions = _actions_by_name(state)
        score = _hole_score(state, seat_id)
        if "check" in actions:
            if score >= 18 and "bet" in actions:
                return {"action": "bet", "amount": actions["bet"]["min_amount"]}
            return {"action": "check"}
        if score >= 13 and "call" in actions:
            return {"action": "call"}
        return {"action": "fold"}


@dataclass(frozen=True)
class RuleBasedTag:
    def choose_action(self, state: dict, seat_id: int) -> dict:
        actions = _actions_by_name(state)
        score = _hole_score(state, seat_id)
        if "check" in actions:
            if score >= 16 and "bet" in actions:
                return {"action": "bet", "amount": _sized_amount(actions["bet"], state, 0.5)}
            return {"action": "check"}
        if score >= 17 and "raise" in actions and actions["raise"].get("full_raise", True):
            return {"action": "raise", "amount": actions["raise"]["min_amount"]}
        if score >= 10 and "call" in actions:
            return {"action": "call"}
        return {"action": "fold"}


@dataclass(frozen=True)
class RuleBasedPro:
    def choose_action(self, state: dict, seat_id: int) -> dict:
        actions = _actions_by_name(state)
        score = _hole_score(state, seat_id)
        rng = _bot_rng(state, seat_id)
        if "check" in actions:
            if score >= 14 and "bet" in actions:
                fraction = 0.75 if rng.random() > 0.35 else 0.5
                return {"action": "bet", "amount": _sized_amount(actions["bet"], state, fraction)}
            return {"action": "check"}
        if score >= 15 and "raise" in actions and actions["raise"].get("full_raise", True):
            return {"action": "raise", "amount": _sized_amount(actions["raise"], state, 0.75)}
        if score >= 8 and "call" in actions:
            return {"action": "call"}
        return {"action": "fold"}


STRATEGIES: dict[str, BotStrategy] = {
    "random": RandomBot(),
    "fish": RuleBasedFish(),
    "tight": RuleBasedTight(),
    "tag": RuleBasedTag(),
    "pro": RuleBasedPro(),
    "pro_tag": RuleBasedPro(),
    "pro_lag": RuleBasedPro(),
    "pro_exploit": RuleBasedPro(),
    "pro_balanced": RuleBasedPro(),
}


def assign_bot_personalities(state: dict, difficulty: str) -> dict:
    pool = BOT_PERSONALITY_POOLS.get(difficulty, BEGINNER_POOL)
    bot_seats = [seat for seat in state["seats"] if seat["role"] == "bot"]
    for index, seat in enumerate(bot_seats):
        seat["personality"] = pool[index % len(pool)]
    state["bot_personality_pool"] = (
        difficulty if difficulty in BOT_PERSONALITY_POOLS else "beginner"
    )
    return state


def advance_bots_until_human_turn(state: dict, *, max_actions: int = 100) -> dict:
    next_state = state
    for _ in range(max_actions):
        if next_state["status"] == "complete" or next_state["to_act"] is None:
            return next_state
        seat = next_state["seats"][next_state["to_act"]]
        if seat["seat"] == HERO_SEAT or seat["role"] != "bot":
            return next_state

        personality = seat.get("personality", "fish")
        strategy = STRATEGIES.get(personality, STRATEGIES["fish"])
        decision = strategy.choose_action(next_state, seat["seat"])
        next_state = apply_action(
            next_state,
            seat_id=seat["seat"],
            action=decision["action"],
            amount=decision.get("amount"),
        )
        _annotate_latest_action(next_state, source="rule_bot")

    raise RuntimeError("Bot action loop exceeded max_actions.")


async def advance_bots_until_human_turn_async(
    state: dict[str, Any],
    *,
    llm_provider: PokerLLMProvider | None = None,
    max_actions: int = 100,
) -> dict[str, Any]:
    next_state = state
    for _ in range(max_actions):
        if next_state["status"] == "complete" or next_state["to_act"] is None:
            return next_state
        seat = next_state["seats"][next_state["to_act"]]
        if seat["seat"] == HERO_SEAT or seat["role"] != "bot":
            return next_state

        decision, source = await _choose_bot_action_async(next_state, seat["seat"], llm_provider)
        next_state = apply_action(
            next_state,
            seat_id=seat["seat"],
            action=decision["action"],
            amount=decision.get("amount"),
        )
        _annotate_latest_action(next_state, source=source)

    raise RuntimeError("Bot action loop exceeded max_actions.")


async def _choose_bot_action_async(
    state: dict[str, Any],
    seat_id: int,
    llm_provider: PokerLLMProvider | None,
) -> tuple[dict[str, Any], str]:
    if state.get("llm_bots_enabled") and llm_provider is not None:
        try:
            timeout = getattr(llm_provider, "decision_timeout", 8)
            async with asyncio.timeout(timeout):
                decision = await llm_provider.choose_action(state, seat_id)
            validated = validate_llm_decision(decision, state)
            if validated is not None:
                return validated, "llm"
            state.setdefault("llm_bot_errors", []).append(
                {"seat": seat_id, "error": "InvalidLLMDecision"}
            )
            fallback_source = "rule_fallback_invalid_llm"
        except Exception as error:
            if _is_llm_auth_error(error):
                raise LLMProviderUnavailable(
                    "LLM opponents are not authorized for the Responses API."
                ) from error
            state.setdefault("llm_bot_errors", []).append(
                {"seat": seat_id, "error": error.__class__.__name__}
            )
            fallback_source = (
                "rule_fallback_timeout"
                if isinstance(error, TimeoutError)
                else "rule_fallback_error"
            )
    elif state.get("llm_bots_enabled"):
        fallback_source = "rule_fallback_no_provider"
    else:
        fallback_source = "rule_bot"

    personality = state["seats"][seat_id].get("personality", "fish")
    strategy = STRATEGIES.get(personality, STRATEGIES["fish"])
    return strategy.choose_action(state, seat_id), fallback_source


def _annotate_latest_action(state: dict[str, Any], *, source: str) -> None:
    if state["hand_history"]:
        state["hand_history"][-1]["source"] = source


def _actions_by_name(state: dict) -> dict:
    return {action["action"]: action for action in legal_actions(state)}


def _hole_score(state: dict, seat_id: int) -> int:
    cards = state["seats"][seat_id]["hole_cards"]
    first, second = cards
    first_rank = RANK_VALUE[first[0]]
    second_rank = RANK_VALUE[second[0]]
    high = max(first_rank, second_rank)
    low = min(first_rank, second_rank)
    suited_bonus = 2 if first[1] == second[1] else 0
    connected_bonus = 2 if high - low <= 1 else 0
    pair_bonus = 8 if high == low else 0
    return high + pair_bonus + suited_bonus + connected_bonus


def _sized_amount(action: dict, state: dict, pot_fraction: float) -> int:
    desired = max(
        action["min_amount"],
        int(max(_live_pot(state), state["stakes"]["big_blind"]) * pot_fraction),
    )
    return min(action["max_amount"], desired)


def _live_pot(state: dict) -> int:
    return sum(seat["committed"] for seat in state["seats"])


def _bot_rng(state: dict, seat_id: int) -> random.Random:
    seed = f"{state.get('seed')}:{seat_id}:{len(state['hand_history'])}"
    return random.Random(seed)


def _is_llm_auth_error(error: Exception) -> bool:
    response = getattr(error, "response", None)
    return getattr(response, "status_code", None) in {401, 403}
