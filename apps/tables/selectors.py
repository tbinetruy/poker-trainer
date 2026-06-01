from django.shortcuts import get_object_or_404

from apps.poker_engine import visible_state
from apps.poker_engine.llm import PERSONALITY_PROMPTS
from apps.tables.models import GameSession


def serialize_game(game: GameSession) -> dict:
    return {
        "id": str(game.id),
        "difficulty": game.difficulty,
        "status": game.status,
        "table_state": visible_state(game.table_state),
        "created_at": game.created_at.isoformat(),
        "updated_at": game.updated_at.isoformat(),
    }


def serialize_game_review(game: GameSession) -> dict:
    state = game.table_state
    return {
        "game_id": str(game.id),
        "status": game.status,
        "table": {
            "community_cards": list(state["community_cards"]),
            "button_seat": state["button_seat"],
            "winners": list(state.get("winners", [])),
        },
        "seats": [_review_seat(seat) for seat in state["seats"]],
    }


def get_game_snapshot(game_id: str) -> dict:
    game = get_object_or_404(GameSession, id=game_id)
    return serialize_game(game)


async def get_game_snapshot_async(game_id: str) -> dict | None:
    try:
        game = await GameSession.objects.aget(id=game_id)
    except GameSession.DoesNotExist:
        return None

    return serialize_game(game)


def _review_seat(seat: dict) -> dict:
    personality = seat.get("personality")
    return {
        "seat": seat["seat"],
        "name": seat["name"],
        "role": seat["role"],
        "position": seat["position"],
        "status": seat["status"],
        "stack": seat["stack"],
        "committed": seat["committed"],
        "street_bet": seat["street_bet"],
        "hole_cards": list(seat["hole_cards"]),
        "personality": personality,
        "personality_brief": PERSONALITY_PROMPTS.get(personality) if personality else None,
    }
