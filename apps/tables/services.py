import uuid

from apps.poker_engine import create_hand
from apps.poker_engine.bots import advance_bots_until_human_turn, assign_bot_personalities
from apps.tables.models import GameSession


def build_initial_table_state(difficulty: str, seed: str | None = None) -> dict:
    state = create_hand(difficulty=difficulty, seed=seed or str(uuid.uuid4()))
    state = assign_bot_personalities(state, difficulty)
    return advance_bots_until_human_turn(state)


def create_game_session(difficulty: str) -> GameSession:
    if difficulty not in GameSession.Difficulty.values:
        difficulty = GameSession.Difficulty.BEGINNER
    game_id = uuid.uuid4()

    return GameSession.objects.create(
        id=game_id,
        difficulty=difficulty,
        status=GameSession.Status.ACTIVE,
        table_state=build_initial_table_state(difficulty, seed=str(game_id)),
    )
