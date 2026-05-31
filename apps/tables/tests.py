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
    assert game.status == GameSession.Status.WAITING
    assert game.table_state["variant"] == "no_limit_holdem"
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
