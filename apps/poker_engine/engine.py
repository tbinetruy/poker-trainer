import random
from copy import deepcopy
from typing import Any

from apps.poker_engine.evaluator import RANKS, evaluate_seven

SUITS = "cdhs"
STREETS = ["preflop", "flop", "turn", "river"]
SEATS = [
    {"seat": 0, "name": "Hero", "role": "human", "position": "BTN"},
    {"seat": 1, "name": "Villain 1", "role": "bot", "position": "SB"},
    {"seat": 2, "name": "Villain 2", "role": "bot", "position": "BB"},
    {"seat": 3, "name": "Villain 3", "role": "bot", "position": "UTG"},
    {"seat": 4, "name": "Villain 4", "role": "bot", "position": "CO"},
]


class InvalidAction(ValueError):
    pass


def create_hand(
    *,
    difficulty: str,
    seed: int | str,
    small_blind: int = 50,
    big_blind: int = 100,
    starting_stack: int = 10_000,
    button_seat: int = 0,
) -> dict[str, Any]:
    deck = _shuffled_deck(seed)
    seats = []
    for seat in SEATS:
        seats.append(
            {
                **seat,
                "stack": starting_stack,
                "hole_cards": [deck.pop(), deck.pop()],
                "status": "active",
                "committed": 0,
                "street_bet": 0,
            }
        )

    state = {
        "variant": "no_limit_holdem",
        "difficulty": difficulty,
        "seed": str(seed),
        "hand_id": "1",
        "stakes": {"small_blind": small_blind, "big_blind": big_blind},
        "button_seat": button_seat,
        "status": "active",
        "street": "preflop",
        "community_cards": [],
        "deck": deck,
        "seats": seats,
        "pot": 0,
        "current_bet": 0,
        "min_raise": big_blind,
        "to_act": None,
        "acted_seats": [],
        "hand_history": [],
        "last_action": None,
        "winners": [],
    }

    _post_blind(state, seat_id=1, amount=small_blind, blind_type="small_blind")
    _post_blind(state, seat_id=2, amount=big_blind, blind_type="big_blind")
    state["current_bet"] = big_blind
    state["to_act"] = _next_active_seat(state, after_seat=2)
    state["legal_actions"] = legal_actions(state)
    return state


def legal_actions(state: dict[str, Any]) -> list[dict[str, Any]]:
    seat_id = state.get("to_act")
    if seat_id is None or state["street"] == "showdown":
        return []

    seat = _seat(state, seat_id)
    if seat["status"] != "active" or seat["stack"] <= 0:
        return []

    call_amount = max(0, state["current_bet"] - seat["street_bet"])
    actions: list[dict[str, Any]] = []

    if call_amount == 0:
        actions.append({"action": "check"})
        if seat["stack"] > 0:
            min_bet = min(state["stakes"]["big_blind"], seat["stack"])
            actions.append({"action": "bet", "min_amount": min_bet, "max_amount": seat["stack"]})
        return actions

    actions.append({"action": "fold"})
    actions.append({"action": "call", "amount": min(call_amount, seat["stack"])})

    min_total = state["current_bet"] + state["min_raise"]
    max_total = seat["street_bet"] + seat["stack"]
    if max_total > state["current_bet"]:
        can_make_full_raise = max_total >= min_total
        actions.append(
            {
                "action": "raise",
                "full_raise": can_make_full_raise,
                "min_amount": min_total if can_make_full_raise else max_total,
                "max_amount": max_total,
            }
        )

    return actions


def apply_action(
    state: dict[str, Any],
    *,
    seat_id: int,
    action: str,
    amount: int | None = None,
) -> dict[str, Any]:
    next_state = deepcopy(state)
    if next_state["to_act"] != seat_id:
        raise InvalidAction("It is not this seat's turn.")

    available = {item["action"]: item for item in legal_actions(next_state)}
    if action not in available:
        raise InvalidAction(f"Action {action!r} is not legal.")

    seat = _seat(next_state, seat_id)
    previous_bet = next_state["current_bet"]

    if action == "fold":
        seat["status"] = "folded"
        _record(next_state, seat_id, "fold")
    elif action == "check":
        _record(next_state, seat_id, "check")
    elif action == "call":
        paid = _commit_chips(seat, available[action]["amount"])
        _record(next_state, seat_id, "call", amount=paid)
    elif action == "bet":
        bet_size = _validated_amount(amount, available[action])
        paid = _commit_chips(seat, bet_size)
        next_state["current_bet"] = seat["street_bet"]
        next_state["min_raise"] = paid
        next_state["acted_seats"] = []
        _record(next_state, seat_id, "bet", amount=paid)
    elif action == "raise":
        target_total = _validated_amount(amount, available[action])
        paid = _commit_chips(seat, target_total - seat["street_bet"])
        next_state["current_bet"] = seat["street_bet"]
        raise_size = next_state["current_bet"] - previous_bet
        if available[action]["full_raise"]:
            next_state["min_raise"] = raise_size
            next_state["acted_seats"] = []
        _record(
            next_state,
            seat_id,
            "raise",
            amount=paid,
            total=seat["street_bet"],
            full_raise=available[action]["full_raise"],
        )

    if seat["stack"] == 0 and seat["status"] == "active":
        seat["status"] = "all_in"

    if seat_id not in next_state["acted_seats"]:
        next_state["acted_seats"].append(seat_id)

    next_state["pot"] = _pot(next_state)
    _advance_after_action(next_state, seat_id)
    next_state["legal_actions"] = legal_actions(next_state)
    return next_state


def visible_state(state: dict[str, Any], *, hero_seat: int = 0) -> dict[str, Any]:
    visible = deepcopy(state)
    visible.pop("deck", None)
    visible.pop("seed", None)
    visible.pop("acted_seats", None)

    for seat in visible["seats"]:
        if seat["seat"] == hero_seat:
            continue
        if visible["status"] != "complete" or seat["status"] == "folded":
            seat["hole_cards"] = []

    visible["legal_actions"] = legal_actions(state)
    return visible


def _advance_after_action(state: dict[str, Any], acted_seat: int) -> None:
    remaining = [seat for seat in state["seats"] if seat["status"] != "folded"]
    if len(remaining) == 1:
        _award_uncontested(state, remaining[0])
        return

    next_actor = _next_seat_needing_action(state, after_seat=acted_seat)
    if next_actor is not None:
        state["to_act"] = next_actor
        return

    _advance_street(state)


def _advance_street(state: dict[str, Any]) -> None:
    active_with_chips = [
        seat for seat in state["seats"] if seat["status"] == "active" and seat["stack"] > 0
    ]
    if len(active_with_chips) <= 1:
        _deal_remaining_board(state)
        _showdown(state)
        return

    street = state["street"]
    if street == "preflop":
        state["community_cards"].extend(
            [state["deck"].pop(), state["deck"].pop(), state["deck"].pop()]
        )
        state["street"] = "flop"
    elif street == "flop":
        state["community_cards"].append(state["deck"].pop())
        state["street"] = "turn"
    elif street == "turn":
        state["community_cards"].append(state["deck"].pop())
        state["street"] = "river"
    elif street == "river":
        _showdown(state)
        return

    for seat in state["seats"]:
        seat["street_bet"] = 0
    state["current_bet"] = 0
    state["min_raise"] = state["stakes"]["big_blind"]
    state["acted_seats"] = []
    state["to_act"] = _next_active_seat(state, after_seat=state["button_seat"])
    state["last_action"] = f"deal_{state['street']}"
    _record(state, None, state["last_action"], cards=list(state["community_cards"]))


def _showdown(state: dict[str, Any]) -> None:
    contenders = [seat for seat in state["seats"] if seat["status"] != "folded"]
    ranked = {
        seat["seat"]: evaluate_seven(seat["hole_cards"] + state["community_cards"])
        for seat in contenders
    }
    winner_amounts = _pay_showdown_pots(state, contenders, ranked)
    state["street"] = "showdown"
    state["status"] = "complete"
    state["to_act"] = None
    state["winners"] = [
        {"seat": seat_id, "amount": amount}
        for seat_id, amount in sorted(winner_amounts.items())
        if amount > 0
    ]
    _record(state, None, "showdown", winners=state["winners"])


def _award_uncontested(state: dict[str, Any], winner: dict[str, Any]) -> None:
    amount = _pot(state)
    winner["stack"] += amount
    winner["payout"] = amount
    state["pot"] = 0
    state["street"] = "showdown"
    state["status"] = "complete"
    state["to_act"] = None
    state["winners"] = [{"seat": winner["seat"], "amount": amount}]
    _record(state, winner["seat"], "win_uncontested", amount=amount)


def _deal_remaining_board(state: dict[str, Any]) -> None:
    while len(state["community_cards"]) < 5:
        state["community_cards"].append(state["deck"].pop())


def _pay_showdown_pots(
    state: dict[str, Any],
    contenders: list[dict[str, Any]],
    ranked: dict[int, tuple],
) -> dict[int, int]:
    winner_amounts = {seat["seat"]: 0 for seat in contenders}
    levels = sorted({seat["committed"] for seat in state["seats"] if seat["committed"] > 0})
    previous_level = 0

    for level in levels:
        pot_participants = [seat for seat in state["seats"] if seat["committed"] >= level]
        pot_amount = (level - previous_level) * len(pot_participants)
        eligible = [seat for seat in contenders if seat["committed"] >= level]
        best_rank = max(ranked[seat["seat"]] for seat in eligible)
        winners = [seat for seat in eligible if ranked[seat["seat"]] == best_rank]
        share, remainder = divmod(pot_amount, len(winners))

        for index, winner in enumerate(sorted(winners, key=lambda seat: seat["seat"])):
            payout = share + (1 if index < remainder else 0)
            winner["stack"] += payout
            winner["payout"] = winner.get("payout", 0) + payout
            winner_amounts[winner["seat"]] += payout

        previous_level = level

    state["pot"] = 0
    return winner_amounts


def _next_seat_needing_action(state: dict[str, Any], *, after_seat: int) -> int | None:
    for seat_id in _seat_order(after_seat, len(state["seats"])):
        seat = _seat(state, seat_id)
        if seat["status"] != "active" or seat["stack"] <= 0:
            continue
        has_matched_bet = seat["street_bet"] == state["current_bet"]
        has_acted = seat_id in state["acted_seats"]
        if not has_matched_bet or not has_acted:
            return seat_id
    return None


def _next_active_seat(state: dict[str, Any], *, after_seat: int) -> int | None:
    for seat_id in _seat_order(after_seat, len(state["seats"])):
        seat = _seat(state, seat_id)
        if seat["status"] == "active" and seat["stack"] > 0:
            return seat_id
    return None


def _seat_order(after_seat: int, seat_count: int) -> list[int]:
    return [((after_seat + offset) % seat_count) for offset in range(1, seat_count + 1)]


def _seat(state: dict[str, Any], seat_id: int) -> dict[str, Any]:
    return state["seats"][seat_id]


def _post_blind(state: dict[str, Any], *, seat_id: int, amount: int, blind_type: str) -> None:
    seat = _seat(state, seat_id)
    paid = _commit_chips(seat, amount)
    state["pot"] = _pot(state)
    _record(state, seat_id, blind_type, amount=paid)


def _commit_chips(seat: dict[str, Any], amount: int) -> int:
    paid = min(amount, seat["stack"])
    seat["stack"] -= paid
    seat["committed"] += paid
    seat["street_bet"] += paid
    return paid


def _validated_amount(amount: int | None, action: dict[str, Any]) -> int:
    if amount is None:
        raise InvalidAction("This action requires an amount.")
    if amount < action["min_amount"] or amount > action["max_amount"]:
        raise InvalidAction("Amount is outside the legal range.")
    return amount


def _pot(state: dict[str, Any]) -> int:
    return sum(seat["committed"] for seat in state["seats"])


def _record(state: dict[str, Any], seat_id: int | None, action: str, **extra: Any) -> None:
    event = {"street": state["street"], "seat": seat_id, "action": action, **extra}
    state["hand_history"].append(event)
    state["last_action"] = action


def _shuffled_deck(seed: int | str) -> list[str]:
    deck = [f"{rank}{suit}" for suit in SUITS for rank in RANKS]
    rng = random.Random(str(seed))
    rng.shuffle(deck)
    return deck
