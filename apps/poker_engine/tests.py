import asyncio
import json
from pathlib import Path

import pytest
from asgiref.sync import async_to_sync

from apps.poker_engine import apply_action, create_hand, legal_actions, visible_state
from apps.poker_engine.bots import (
    BOT_PERSONALITY_POOLS,
    advance_bots_until_human_turn,
    advance_bots_until_human_turn_async,
    assign_bot_personalities,
)
from apps.poker_engine.engine import InvalidAction, _showdown
from apps.poker_engine.evaluator import evaluate_seven
from apps.poker_engine.llm import (
    CodexCLIPokerProvider,
    LLMProviderUnavailable,
    OpenAIResponsesPokerProvider,
    build_llm_decision_context,
    load_openai_api_key,
    validate_llm_decision,
)


def test_new_hand_posts_blinds_and_sets_preflop_action() -> None:
    state = create_hand(difficulty="beginner", seed="hand-1")

    assert state["street"] == "preflop"
    assert state["pot"] == 150
    assert state["current_bet"] == 100
    assert state["to_act"] == 3
    assert state["seats"][1]["street_bet"] == 50
    assert state["seats"][2]["street_bet"] == 100
    assert {action["action"] for action in legal_actions(state)} == {"fold", "call", "raise"}


def test_new_hand_rotates_button_and_blinds() -> None:
    state = create_hand(difficulty="beginner", seed="rotated-button", button_seat=2)

    assert state["button_seat"] == 2
    assert [seat["position"] for seat in state["seats"]] == ["UTG", "CO", "BTN", "SB", "BB"]
    assert state["seats"][3]["street_bet"] == 50
    assert state["seats"][4]["street_bet"] == 100
    assert state["to_act"] == 0
    assert state["hand_history"][:2] == [
        {"street": "preflop", "seat": 3, "action": "small_blind", "amount": 50},
        {"street": "preflop", "seat": 4, "action": "big_blind", "amount": 100},
    ]


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


def test_bot_sizing_uses_live_committed_pot() -> None:
    from apps.poker_engine.bots import STRATEGIES

    state = assign_bot_personalities(
        create_hand(difficulty="advanced", seed="live-pot-sizing"),
        "advanced",
    )
    state["street"] = "flop"
    state["current_bet"] = 0
    state["pot"] = 0
    state["to_act"] = 1
    state["acted_seats"] = []
    state["community_cards"] = ["2c", "7d", "Jh"]
    state["seats"][1]["hole_cards"] = ["As", "Ah"]
    for seat in state["seats"]:
        seat["street_bet"] = 0
        seat["committed"] = 200

    decision = STRATEGIES["pro"].choose_action(state, 1)

    assert decision == {"action": "bet", "amount": 750}


def test_llm_decision_context_only_reveals_acting_bot_private_information() -> None:
    state = assign_bot_personalities(
        create_hand(difficulty="advanced", seed="llm-redaction"),
        "advanced",
    )

    context = build_llm_decision_context(state, seat_id=3)

    assert context["acting_player"]["hole_cards"] == state["seats"][3]["hole_cards"]
    assert context["acting_player"]["personality"] == state["seats"][3]["personality"]
    assert context["table"]["seats"][3]["hole_cards"] == state["seats"][3]["hole_cards"]
    assert context["table"]["seats"][0]["hole_cards"] == []
    assert context["table"]["seats"][1]["hole_cards"] == []
    assert "deck" not in context
    assert "seed" not in context
    assert "personality" not in context["table"]["seats"][1]


def test_validate_llm_decision_rejects_illegal_amount() -> None:
    state = assign_bot_personalities(
        create_hand(difficulty="advanced", seed="llm-validation"),
        "advanced",
    )

    decision = validate_llm_decision({"action": "raise", "amount": 10}, state)

    assert decision is None


def test_load_openai_api_key_prefers_environment(monkeypatch, tmp_path) -> None:
    auth_path = tmp_path / "auth.json"
    auth_path.write_text('{"OPENAI_API_KEY":"from-file"}')
    monkeypatch.setenv("OPENAI_API_KEY", "from-env")

    assert load_openai_api_key(auth_path) == "from-env"


def test_load_openai_api_key_falls_back_to_codex_access_token(monkeypatch, tmp_path) -> None:
    auth_path = tmp_path / "auth.json"
    auth_path.write_text('{"OPENAI_API_KEY":null,"tokens":{"access_token":"codex-token"}}')
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert load_openai_api_key(auth_path) == "codex-token"


def test_async_bot_uses_valid_llm_decision() -> None:
    class Provider:
        max_decisions_per_advance = 10

        async def choose_action(self, state, seat_id):
            return {"action": "call", "amount": 100, "confidence": 0.8, "rationale": "priced in"}

    state = assign_bot_personalities(
        create_hand(difficulty="advanced", seed="llm-valid-decision"),
        "advanced",
    )
    state["llm_bots_enabled"] = True

    state = async_to_sync(advance_bots_until_human_turn_async)(state, llm_provider=Provider())

    assert state["hand_history"][-2]["action"] == "call"
    assert state["hand_history"][-1]["action"] == "call"
    assert state["to_act"] == 0


def test_async_bot_respects_llm_decision_limit() -> None:
    class Provider:
        max_decisions_per_advance = 1

        def __init__(self):
            self.calls = 0

        async def choose_action(self, state, seat_id):
            self.calls += 1
            return {"action": "call", "amount": 100, "confidence": 0.8, "rationale": "continue"}

    provider = Provider()
    state = assign_bot_personalities(
        create_hand(difficulty="beginner", seed="llm-decision-limit"),
        "beginner",
    )
    state["llm_bots_enabled"] = True

    state = async_to_sync(advance_bots_until_human_turn_async)(state, llm_provider=provider)

    assert provider.calls == 1
    assert state["to_act"] == 0


def test_async_bot_falls_back_when_llm_decision_is_invalid() -> None:
    class Provider:
        max_decisions_per_advance = 10

        async def choose_action(self, state, seat_id):
            return {"action": "raise", "amount": 1, "confidence": 0.8, "rationale": "bad size"}

    state = assign_bot_personalities(
        create_hand(difficulty="beginner", seed="llm-invalid-decision"),
        "beginner",
    )
    state["llm_bots_enabled"] = True

    state = async_to_sync(advance_bots_until_human_turn_async)(state, llm_provider=Provider())

    assert state["hand_history"][-2]["action"] == "call"
    assert state["hand_history"][-1]["action"] == "call"
    assert state["to_act"] == 0
    assert state["llm_bot_errors"] == [
        {"seat": 3, "error": "InvalidLLMDecision"},
        {"seat": 4, "error": "InvalidLLMDecision"},
    ]


def test_async_bot_falls_back_when_llm_times_out(monkeypatch) -> None:
    class Provider:
        max_decisions_per_advance = 10

        async def choose_action(self, state, seat_id):
            await asyncio.sleep(0.01)
            return {"action": "raise", "amount": 500, "confidence": 0.8, "rationale": "late"}

    class ImmediateTimeout:
        async def __aenter__(self):
            raise TimeoutError

        async def __aexit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr("apps.poker_engine.bots.asyncio.timeout", lambda delay: ImmediateTimeout())
    state = assign_bot_personalities(
        create_hand(difficulty="beginner", seed="llm-timeout"),
        "beginner",
    )
    state["llm_bots_enabled"] = True

    state = async_to_sync(advance_bots_until_human_turn_async)(state, llm_provider=Provider())

    assert state["to_act"] == 0
    assert state["llm_bot_errors"] == [
        {"seat": 3, "error": "TimeoutError"},
        {"seat": 4, "error": "TimeoutError"},
    ]


def test_async_bot_raises_when_llm_is_unauthorized() -> None:
    class Response:
        status_code = 401

    class UnauthorizedError(Exception):
        response = Response()

    class Provider:
        async def choose_action(self, state, seat_id):
            raise UnauthorizedError

    state = assign_bot_personalities(
        create_hand(difficulty="beginner", seed="llm-unauthorized"),
        "beginner",
    )
    state["llm_bots_enabled"] = True

    with pytest.raises(LLMProviderUnavailable):
        async_to_sync(advance_bots_until_human_turn_async)(state, llm_provider=Provider())


def test_openai_provider_sends_redacted_structured_output_request() -> None:
    import httpx

    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["authorization"]
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "content": [
                            {
                                "type": "output_text",
                                "text": (
                                    '{"action":"call","amount":100,'
                                    '"confidence":0.7,"rationale":"continue"}'
                                ),
                            }
                        ]
                    }
                ]
            },
        )

    state = assign_bot_personalities(
        create_hand(difficulty="advanced", seed="llm-provider"),
        "advanced",
    )
    provider = OpenAIResponsesPokerProvider(
        api_key="test-key",
        model="test-model",
        base_url="https://example.test/v1",
        transport=httpx.MockTransport(handler),
    )

    decision = async_to_sync(provider.choose_action)(state, 3)
    prompt_context = json.loads(captured["body"]["input"][1]["content"][0]["text"])

    assert decision == {
        "action": "call",
        "amount": 100,
        "confidence": 0.7,
        "rationale": "continue",
    }
    assert captured["url"] == "https://example.test/v1/responses"
    assert captured["authorization"] == "Bearer test-key"
    assert captured["body"]["model"] == "test-model"
    assert captured["body"]["text"]["format"]["type"] == "json_schema"
    assert captured["body"]["text"]["format"]["strict"] is True
    assert prompt_context["acting_player"]["hole_cards"] == state["seats"][3]["hole_cards"]
    assert prompt_context["table"]["seats"][0]["hole_cards"] == []
    assert prompt_context["table"]["seats"][1]["hole_cards"] == []


def test_codex_cli_provider_parses_output_file(monkeypatch) -> None:
    class Process:
        returncode = 0

        async def communicate(self, prompt):
            assert b"Poker context" in prompt
            return b"", b""

    async def create_process(*args, **kwargs):
        output_path = Path(args[args.index("--output-last-message") + 1])
        output_path.write_text(
            '{"action":"call","amount":100,"confidence":0.6,"rationale":"continue"}'
        )
        return Process()

    monkeypatch.setattr("apps.poker_engine.llm.asyncio.create_subprocess_exec", create_process)
    state = assign_bot_personalities(
        create_hand(difficulty="beginner", seed="codex-cli-provider"),
        "beginner",
    )
    provider = CodexCLIPokerProvider(command="codex-test")

    decision = async_to_sync(provider.choose_action)(state, 3)

    assert decision == {
        "action": "call",
        "amount": 100,
        "confidence": 0.6,
        "rationale": "continue",
    }
