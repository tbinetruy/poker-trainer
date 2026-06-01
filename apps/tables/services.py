import uuid

from apps.poker_engine import create_hand
from apps.poker_engine.bots import (
    advance_bots_until_human_turn,
    advance_bots_until_human_turn_async,
    assign_bot_personalities,
)
from apps.poker_engine.llm import PokerLLMProvider
from apps.tables.models import GameSession


def build_initial_table_state(
    difficulty: str,
    seed: str | None = None,
    *,
    llm_bots_enabled: bool = False,
    button_seat: int = 0,
) -> dict:
    state = create_hand(
        difficulty=difficulty,
        seed=seed or str(uuid.uuid4()),
        button_seat=button_seat,
    )
    state = assign_bot_personalities(state, difficulty)
    state["llm_bots_enabled"] = llm_bots_enabled
    return advance_bots_until_human_turn(state)


async def build_initial_table_state_async(
    difficulty: str,
    seed: str | None = None,
    *,
    llm_bots_enabled: bool = False,
    llm_provider: PokerLLMProvider | None = None,
    button_seat: int = 0,
) -> dict:
    state = create_hand(
        difficulty=difficulty,
        seed=seed or str(uuid.uuid4()),
        button_seat=button_seat,
    )
    state = assign_bot_personalities(state, difficulty)
    state["llm_bots_enabled"] = llm_bots_enabled
    if llm_bots_enabled:
        return advance_bots_until_human_turn(state)
    return await advance_bots_until_human_turn_async(state, llm_provider=llm_provider)


def create_game_session(difficulty: str) -> GameSession:
    if difficulty not in GameSession.Difficulty.values:
        difficulty = GameSession.Difficulty.BEGINNER
    game_id = uuid.uuid4()
    button_seat = GameSession.objects.count() % 5

    return GameSession.objects.create(
        id=game_id,
        difficulty=difficulty,
        status=GameSession.Status.ACTIVE,
        table_state=build_initial_table_state(
            difficulty,
            seed=str(game_id),
            button_seat=button_seat,
        ),
    )
