import uuid

import pytest
from asgiref.sync import async_to_sync
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import AsyncClient
from django.urls import path, reverse

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
