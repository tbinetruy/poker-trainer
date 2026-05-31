from django.shortcuts import get_object_or_404

from apps.tables.models import GameSession


def serialize_game(game: GameSession) -> dict:
    return {
        "id": str(game.id),
        "difficulty": game.difficulty,
        "status": game.status,
        "table_state": game.table_state,
        "created_at": game.created_at.isoformat(),
        "updated_at": game.updated_at.isoformat(),
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
