import uuid

import pytest
from asgiref.sync import async_to_sync
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import AsyncClient
from django.urls import path, reverse

from apps.poker_engine.llm import CodexCLIPokerProvider, LLMProviderUnavailable
from apps.tables.consumers import TableConsumer
from apps.tables.models import GameSession
from apps.tables.services import create_game_session

pytestmark = pytest.mark.django_db


def test_create_game_session_builds_initial_table_state() -> None:
    game = create_game_session(GameSession.Difficulty.BEGINNER)

    assert game.difficulty == GameSession.Difficulty.BEGINNER
    assert game.status == GameSession.Status.ACTIVE
    assert game.table_state["variant"] == "no_limit_holdem"
    assert game.table_state["street"] == "preflop"
    assert game.table_state["pot"] >= 250
    assert game.table_state["to_act"] == 0
    assert len(game.table_state["seats"]) == 5
    assert [seat["personality"] for seat in game.table_state["seats"][1:]] == [
        "fish",
        "fish",
        "fish",
        "tight",
    ]


@pytest.mark.django_db(transaction=True)
def test_create_game_endpoint_returns_session() -> None:
    client = AsyncClient()
    response = async_to_sync(client.post)(
        reverse("game-list"),
        data={"difficulty": "beginner"},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["difficulty"] == "beginner"
    assert response.json()["status"] == "active"
    assert response.json()["table_state"]["to_act"] == 0
    assert response.json()["table_state"]["seats"][1]["hole_cards"] == []
    assert "personality" not in response.json()["table_state"]["seats"][1]
    assert GameSession.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_create_game_endpoint_can_enable_llm_bots(monkeypatch) -> None:
    class Provider:
        async def choose_action(self, state, seat_id):
            return {"action": "call", "amount": 100, "confidence": 0.8, "rationale": "continue"}

    monkeypatch.setattr("apps.tables.views.get_default_llm_provider", lambda: Provider())
    client = AsyncClient()
    response = async_to_sync(client.post)(
        reverse("game-list"),
        data={"difficulty": "beginner", "llm_bots": True},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["table_state"]["llm_bots_enabled"] is True
    assert response.json()["table_state"]["to_act"] == 0


@pytest.mark.django_db(transaction=True)
def test_create_game_endpoint_rejects_llm_bots_when_unconfigured(monkeypatch) -> None:
    monkeypatch.setattr("apps.tables.views.get_default_llm_provider", lambda: None)
    client = AsyncClient()
    response = async_to_sync(client.post)(
        reverse("game-list"),
        data={"difficulty": "beginner", "llm_bots": True},
        content_type="application/json",
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "LLM opponents are not configured."
    assert GameSession.objects.count() == 0


def test_default_llm_provider_uses_codex_cli(settings, tmp_path) -> None:
    from apps.tables.llm import get_default_llm_provider

    auth_path = tmp_path / "auth.json"
    auth_path.write_text('{"tokens":{"access_token":"codex-token"}}')
    settings.POKER_LLM_PROVIDER = "codex_cli"
    settings.POKER_OPENAI_AUTH_PATH = str(auth_path)

    provider = get_default_llm_provider()

    assert isinstance(provider, CodexCLIPokerProvider)


@pytest.mark.django_db(transaction=True)
def test_create_game_endpoint_rejects_unauthorized_llm_provider(monkeypatch) -> None:
    async def build_state(*args, **kwargs):
        raise LLMProviderUnavailable("LLM opponents are not authorized.")

    monkeypatch.setattr("apps.tables.views.get_default_llm_provider", lambda: object())
    monkeypatch.setattr("apps.tables.views.build_initial_table_state_async", build_state)
    client = AsyncClient()
    response = async_to_sync(client.post)(
        reverse("game-list"),
        data={"difficulty": "beginner", "llm_bots": True},
        content_type="application/json",
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "LLM opponents are not authorized."
    assert GameSession.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_create_game_endpoint_rejects_malformed_json() -> None:
    client = AsyncClient()
    response = async_to_sync(client.post)(
        reverse("game-list"),
        data=b"{bad-json",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Malformed JSON."
    assert GameSession.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_game_action_endpoint_applies_hero_action() -> None:
    game = create_game_session(GameSession.Difficulty.BEGINNER)

    client = AsyncClient()
    response = async_to_sync(client.post)(
        reverse("game-action", kwargs={"game_id": game.id}),
        data={"seat": 0, "action": "call"},
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["table_state"]["seats"][0]["stack"] == 9_900
    assert payload["table_state"]["street"] == "flop"
    assert payload["table_state"]["to_act"] == 0


@pytest.mark.django_db(transaction=True)
def test_game_action_endpoint_rejects_non_hero_action() -> None:
    game = create_game_session(GameSession.Difficulty.BEGINNER)

    client = AsyncClient()
    response = async_to_sync(client.post)(
        reverse("game-action", kwargs={"game_id": game.id}),
        data={"seat": 3, "action": "call"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only hero actions are accepted through this endpoint."


@pytest.mark.django_db(transaction=True)
def test_game_advice_endpoint_returns_coach_answer(monkeypatch) -> None:
    class Provider:
        async def advise_hero(self, state, *, question, hero_seat=0, include_private_review=False):
            assert question == "What should I do?"
            assert state["seats"][hero_seat]["role"] == "human"
            assert include_private_review is False
            return "Call is reasonable, but raising applies pressure."

    game = create_game_session(GameSession.Difficulty.BEGINNER)
    monkeypatch.setattr("apps.tables.views.get_default_llm_provider", lambda: Provider())
    client = AsyncClient()
    response = async_to_sync(client.post)(
        reverse("game-advice", kwargs={"game_id": game.id}),
        data={"question": "What should I do?"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {"answer": "Call is reasonable, but raising applies pressure."}


@pytest.mark.django_db(transaction=True)
def test_game_review_endpoint_reveals_private_completed_hand_data() -> None:
    game = create_game_session(GameSession.Difficulty.MEDIUM)
    game.table_state["status"] = "complete"
    game.table_state["street"] = "showdown"
    game.status = GameSession.Status.COMPLETE
    game.save(update_fields=["status", "table_state", "updated_at"])

    client = AsyncClient()
    response = async_to_sync(client.post)(reverse("game-review", kwargs={"game_id": game.id}))

    assert response.status_code == 200
    game.refresh_from_db()
    payload = response.json()
    assert payload["game_id"] == str(game.id)
    assert payload["seats"][1]["hole_cards"] == game.table_state["seats"][1]["hole_cards"]
    assert payload["seats"][1]["personality"] == game.table_state["seats"][1]["personality"]
    assert payload["seats"][1]["personality_brief"]
    assert game.table_state["private_review_revealed"] is True


@pytest.mark.django_db(transaction=True)
def test_game_review_endpoint_is_only_available_after_completion() -> None:
    game = create_game_session(GameSession.Difficulty.BEGINNER)

    client = AsyncClient()
    response = async_to_sync(client.post)(reverse("game-review", kwargs={"game_id": game.id}))

    assert response.status_code == 409
    assert response.json()["detail"] == "Review is available after the hand is complete."


@pytest.mark.django_db(transaction=True)
def test_game_advice_endpoint_can_include_private_review_after_completion(monkeypatch) -> None:
    class Provider:
        async def advise_hero(self, state, *, question, hero_seat=0, include_private_review=False):
            assert question == "What did Villain 1 have?"
            assert include_private_review is True
            return "Villain 1 had the revealed hand and a private bot personality."

    game = create_game_session(GameSession.Difficulty.BEGINNER)
    game.table_state["status"] = "complete"
    game.table_state["street"] = "showdown"
    game.table_state["private_review_revealed"] = True
    game.status = GameSession.Status.COMPLETE
    game.save(update_fields=["status", "table_state", "updated_at"])
    monkeypatch.setattr("apps.tables.views.get_default_llm_provider", lambda: Provider())

    client = AsyncClient()
    response = async_to_sync(client.post)(
        reverse("game-advice", kwargs={"game_id": game.id}),
        data={"question": "What did Villain 1 have?", "include_private_review": True},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert (
        response.json()["answer"]
        == "Villain 1 had the revealed hand and a private bot personality."
    )


@pytest.mark.django_db(transaction=True)
def test_game_advice_endpoint_rejects_private_review_during_active_hand() -> None:
    game = create_game_session(GameSession.Difficulty.BEGINNER)
    client = AsyncClient()
    response = async_to_sync(client.post)(
        reverse("game-advice", kwargs={"game_id": game.id}),
        data={"question": "What do they have?", "include_private_review": True},
        content_type="application/json",
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Private review is available after the hand is complete."


@pytest.mark.django_db(transaction=True)
def test_game_advice_endpoint_requires_reveal_before_private_review(monkeypatch) -> None:
    class Provider:
        async def advise_hero(self, state, *, question, hero_seat=0, include_private_review=False):
            raise AssertionError("Provider should not be called before reveal.")

    game = create_game_session(GameSession.Difficulty.BEGINNER)
    game.table_state["status"] = "complete"
    game.table_state["street"] = "showdown"
    game.status = GameSession.Status.COMPLETE
    game.save(update_fields=["status", "table_state", "updated_at"])
    monkeypatch.setattr("apps.tables.views.get_default_llm_provider", lambda: Provider())

    client = AsyncClient()
    response = async_to_sync(client.post)(
        reverse("game-advice", kwargs={"game_id": game.id}),
        data={"question": "What did they have?", "include_private_review": True},
        content_type="application/json",
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Private review must be revealed before asking the coach."


@pytest.mark.django_db(transaction=True)
def test_game_advice_endpoint_rejects_empty_question() -> None:
    game = create_game_session(GameSession.Difficulty.BEGINNER)
    client = AsyncClient()
    response = async_to_sync(client.post)(
        reverse("game-advice", kwargs={"game_id": game.id}),
        data={"question": "   "},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Question is required."


@pytest.mark.django_db(transaction=True)
def test_table_socket_sends_snapshot_for_existing_game() -> None:
    game = create_game_session(GameSession.Difficulty.BEGINNER)

    async def run_test() -> None:
        communicator = WebsocketCommunicator(
            URLRouter([path("ws/tables/<uuid:game_id>/", TableConsumer.as_asgi())]),
            f"/ws/tables/{game.id}/",
        )

        connected, _ = await communicator.connect()
        assert connected is True
        message = await communicator.receive_json_from()
        assert message["type"] == "table.snapshot"
        assert message["payload"]["id"] == str(game.id)
        await communicator.disconnect()

    async_to_sync(run_test)()


@pytest.mark.django_db(transaction=True)
def test_table_socket_rejects_missing_game() -> None:
    missing_game_id = uuid.uuid4()

    async def run_test() -> None:
        communicator = WebsocketCommunicator(
            URLRouter([path("ws/tables/<uuid:game_id>/", TableConsumer.as_asgi())]),
            f"/ws/tables/{missing_game_id}/",
        )

        connected, close_code = await communicator.connect()
        assert connected is False
        assert close_code == 4404

    async_to_sync(run_test)()
