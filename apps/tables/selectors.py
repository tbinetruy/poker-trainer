from asgiref.sync import sync_to_async
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


get_game_snapshot_async = sync_to_async(get_game_snapshot, thread_sensitive=True)

