import pytest
from asgiref.sync import async_to_sync
from django.test import AsyncClient
from django.urls import reverse

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
