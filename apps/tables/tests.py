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
    game = create_game_session(GameSession.Difficulty.MEDIUM)

    assert game.difficulty == GameSession.Difficulty.MEDIUM
    assert game.status == GameSession.Status.ACTIVE
    assert game.table_state["variant"] == "no_limit_holdem"
    assert game.table_state["street"] == "preflop"
    assert game.table_state["pot"] == 150
    assert len(game.table_state["seats"]) == 5


@pytest.mark.django_db(transaction=True)
def test_create_game_endpoint_returns_session() -> None:
    client = AsyncClient()
    response = async_to_sync(client.post)(
        reverse("game-list"),
        data={"difficulty": "advanced"},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["difficulty"] == "advanced"
    assert response.json()["status"] == "active"
    assert response.json()["table_state"]["seats"][1]["hole_cards"] == []
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
    game.table_state = apply_until_hero_can_call(game.table_state)
    game.save(update_fields=["table_state"])

    client = AsyncClient()
    response = async_to_sync(client.post)(
        reverse("game-action", kwargs={"game_id": game.id}),
        data={"seat": 0, "action": "call"},
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["table_state"]["seats"][0]["stack"] == 9_900
    assert payload["table_state"]["to_act"] == 1


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


def apply_until_hero_can_call(state: dict) -> dict:
    from apps.poker_engine import apply_action

    state = apply_action(state, seat_id=3, action="call")
    return apply_action(state, seat_id=4, action="call")


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
