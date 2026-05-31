import pytest

from apps.poker_engine import apply_action, create_hand, legal_actions, visible_state
from apps.poker_engine.bots import (
    BOT_PERSONALITY_POOLS,
    advance_bots_until_human_turn,
    assign_bot_personalities,
)
from apps.poker_engine.engine import InvalidAction, _showdown
from apps.poker_engine.evaluator import evaluate_seven


def test_new_hand_posts_blinds_and_sets_preflop_action() -> None:
    state = create_hand(difficulty="beginner", seed="hand-1")

    assert state["street"] == "preflop"
    assert state["pot"] == 150
    assert state["current_bet"] == 100
    assert state["to_act"] == 3
    assert state["seats"][1]["street_bet"] == 50
    assert state["seats"][2]["street_bet"] == 100
    assert {action["action"] for action in legal_actions(state)} == {"fold", "call", "raise"}


def test_preflop_calls_advance_to_flop() -> None:
    state = create_hand(difficulty="beginner", seed="hand-2")

    state = apply_action(state, seat_id=3, action="call")
    state = apply_action(state, seat_id=4, action="call")
    state = apply_action(state, seat_id=0, action="call")
    state = apply_action(state, seat_id=1, action="call")
    state = apply_action(state, seat_id=2, action="check")

    assert state["street"] == "flop"
    assert len(state["community_cards"]) == 3
    assert state["pot"] == 500
    assert state["current_bet"] == 0
    assert state["to_act"] == 1
    assert {action["action"] for action in legal_actions(state)} == {"check", "bet"}


def test_uncontested_pot_is_awarded_when_everyone_folds() -> None:
    state = create_hand(difficulty="beginner", seed="hand-3")

    state = apply_action(state, seat_id=3, action="fold")
    state = apply_action(state, seat_id=4, action="fold")
    state = apply_action(state, seat_id=0, action="fold")
    state = apply_action(state, seat_id=1, action="fold")

    assert state["status"] == "complete"
    assert state["street"] == "showdown"
    assert state["pot"] == 0
    assert state["winners"] == [{"seat": 2, "amount": 150}]
    assert state["seats"][2]["stack"] == 10_050


def test_raise_reopens_action_and_enforces_turn_order() -> None:
    state = create_hand(difficulty="beginner", seed="hand-4")

    state = apply_action(state, seat_id=3, action="raise", amount=300)

    assert state["current_bet"] == 300
    assert state["to_act"] == 4
    with pytest.raises(InvalidAction):
        apply_action(state, seat_id=0, action="call")


def test_short_all_in_raise_does_not_reopen_action() -> None:
    state = create_hand(difficulty="beginner", seed="hand-short-all-in")
    state["seats"][3]["stack"] = 150

    state = apply_action(state, seat_id=3, action="raise", amount=150)
    state = apply_action(state, seat_id=4, action="call")
    state = apply_action(state, seat_id=0, action="call")
    state = apply_action(state, seat_id=1, action="call")
    state = apply_action(state, seat_id=2, action="call")

    assert state["street"] == "flop"


def test_showdown_picks_best_five_card_hand() -> None:
    state = create_hand(difficulty="beginner", seed="hand-5")
    state["street"] = "river"
    state["community_cards"] = ["Kc", "Qd", "Jh", "5s", "2c"]
    state["current_bet"] = 0
    state["acted_seats"] = [2, 3, 4, 0]
    state["to_act"] = 1
    for seat in state["seats"]:
        seat["committed"] = 30
        seat["stack"] = 9_970
        seat["street_bet"] = 0
    state["seats"][0]["hole_cards"] = ["As", "Th"]
    state["seats"][1]["hole_cards"] = ["Ks", "Kh"]
    state["seats"][2]["hole_cards"] = ["9s", "9h"]
    state["seats"][3]["hole_cards"] = ["8s", "8h"]
    state["seats"][4]["hole_cards"] = ["7s", "7h"]

    state = apply_action(state, seat_id=1, action="check")

    assert state["status"] == "complete"
    assert state["winners"] == [{"seat": 0, "amount": 150}]
    assert state["seats"][0]["stack"] == 10_120


def test_visible_state_hides_unrevealed_opponent_hole_cards() -> None:
    state = assign_bot_personalities(create_hand(difficulty="beginner", seed="hand-6"), "beginner")

    public = visible_state(state)

    assert len(public["seats"][0]["hole_cards"]) == 2
    assert public["seats"][1]["hole_cards"] == []
    assert "personality" not in public["seats"][1]
    assert "bot_personality_pool" not in public
    assert "deck" not in public
    assert "seed" not in public


def test_evaluator_handles_wheel_straight() -> None:
    rank = evaluate_seven(["As", "2d", "3c", "4h", "5s", "9c", "Td"])

    assert rank == (4, 5)


def test_showdown_distributes_side_pots() -> None:
    state = create_hand(difficulty="beginner", seed="hand-7")
    state["community_cards"] = ["Kc", "Qd", "Jh", "5s", "2c"]
    state["seats"][0]["hole_cards"] = ["As", "Th"]
    state["seats"][1]["hole_cards"] = ["Ks", "Kh"]
    state["seats"][2]["hole_cards"] = ["9s", "9h"]

    for seat in state["seats"]:
        seat["status"] = "folded"
        seat["committed"] = 0
        seat["stack"] = 0
    for seat_id, committed in [(0, 100), (1, 200), (2, 200)]:
        state["seats"][seat_id]["status"] = "all_in"
        state["seats"][seat_id]["committed"] = committed

    _showdown(state)

    assert state["winners"] == [{"seat": 0, "amount": 300}, {"seat": 1, "amount": 200}]
    assert state["seats"][0]["stack"] == 300
    assert state["seats"][1]["stack"] == 200


def test_difficulty_presets_assign_private_personalities() -> None:
    beginner = assign_bot_personalities(
        create_hand(difficulty="beginner", seed="beginner-bots"),
        "beginner",
    )
    medium = assign_bot_personalities(
        create_hand(difficulty="medium", seed="medium-bots"),
        "medium",
    )
    advanced = assign_bot_personalities(
        create_hand(difficulty="advanced", seed="advanced-bots"),
        "advanced",
    )

    assert [seat["personality"] for seat in beginner["seats"][1:]] == BOT_PERSONALITY_POOLS[
        "beginner"
    ]
    assert [seat["personality"] for seat in medium["seats"][1:]] == BOT_PERSONALITY_POOLS["medium"]
    assert [seat["personality"] for seat in advanced["seats"][1:]] == BOT_PERSONALITY_POOLS[
        "advanced"
    ]
    assert "pro" not in [seat["personality"] for seat in beginner["seats"][1:]]
    assert "pro" in [seat["personality"] for seat in medium["seats"][1:]]


def test_bots_auto_advance_until_hero_turn() -> None:
    state = assign_bot_personalities(
        create_hand(difficulty="beginner", seed="auto-advance"),
        "beginner",
    )

    state = advance_bots_until_human_turn(state)

    assert state["to_act"] == 0
    assert state["status"] == "active"
    assert [event["seat"] for event in state["hand_history"][-2:]] == [3, 4]


def test_random_bot_is_deterministic_for_same_state() -> None:
    from apps.poker_engine.bots import STRATEGIES

    state = assign_bot_personalities(
        create_hand(difficulty="beginner", seed="random-bot"),
        "beginner",
    )

    first = STRATEGIES["random"].choose_action(state, 3)
    second = STRATEGIES["random"].choose_action(state, 3)

    assert first == second
