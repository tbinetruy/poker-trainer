from apps.tables.models import GameSession

SEATS = [
    {"seat": 0, "name": "Hero", "role": "human", "stack": 10_000, "position": "BTN"},
    {"seat": 1, "name": "Villain 1", "role": "bot", "stack": 10_000, "position": "SB"},
    {"seat": 2, "name": "Villain 2", "role": "bot", "stack": 10_000, "position": "BB"},
    {"seat": 3, "name": "Villain 3", "role": "bot", "stack": 10_000, "position": "UTG"},
    {"seat": 4, "name": "Villain 4", "role": "bot", "stack": 10_000, "position": "CO"},
]


def build_initial_table_state(difficulty: str) -> dict:
    return {
        "variant": "no_limit_holdem",
        "stakes": {"small_blind": 50, "big_blind": 100},
        "street": "lobby",
        "button_seat": 0,
        "pot": 0,
        "to_act": None,
        "community_cards": [],
        "seats": SEATS,
        "last_action": None,
        "difficulty": difficulty,
    }


def create_game_session(difficulty: str) -> GameSession:
    if difficulty not in GameSession.Difficulty.values:
        difficulty = GameSession.Difficulty.BEGINNER

    return GameSession.objects.create(
        difficulty=difficulty,
        status=GameSession.Status.WAITING,
        table_state=build_initial_table_state(difficulty),
    )

