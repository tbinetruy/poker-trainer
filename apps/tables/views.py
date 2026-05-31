import json
from asyncio import Lock

from channels.layers import get_channel_layer
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from apps.poker_engine import apply_action
from apps.poker_engine.engine import InvalidAction
from apps.tables.models import GameSession
from apps.tables.selectors import serialize_game
from apps.tables.services import build_initial_table_state

_ACTION_LOCKS: dict[str, Lock] = {}


async def health(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok"})


@csrf_exempt
async def create_game(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Malformed JSON."}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({"detail": "JSON body must be an object."}, status=400)

    difficulty = payload.get("difficulty", GameSession.Difficulty.BEGINNER)
    if difficulty not in GameSession.Difficulty.values:
        difficulty = GameSession.Difficulty.BEGINNER

    game = await GameSession.objects.acreate(
        difficulty=difficulty,
        status=GameSession.Status.ACTIVE,
        table_state=build_initial_table_state(difficulty),
    )
    return JsonResponse(serialize_game(game), status=201)


async def game_detail(request: HttpRequest, game_id) -> JsonResponse:
    if request.method != "GET":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    try:
        game = await GameSession.objects.aget(id=game_id)
    except GameSession.DoesNotExist:
        return JsonResponse({"detail": "Not found."}, status=404)

    return JsonResponse(serialize_game(game))


@csrf_exempt
async def game_action(request: HttpRequest, game_id) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Malformed JSON."}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({"detail": "JSON body must be an object."}, status=400)

    lock = _ACTION_LOCKS.setdefault(str(game_id), Lock())
    async with lock:
        try:
            game = await GameSession.objects.aget(id=game_id)
        except GameSession.DoesNotExist:
            return JsonResponse({"detail": "Not found."}, status=404)

        try:
            seat_id = int(payload.get("seat", 0))
            if seat_id != 0:
                raise InvalidAction("Only hero actions are accepted through this endpoint.")
            amount = payload.get("amount")
            if amount is not None:
                amount = int(amount)
            game.table_state = apply_action(
                game.table_state,
                seat_id=seat_id,
                action=str(payload.get("action", "")),
                amount=amount,
            )
        except (InvalidAction, TypeError, ValueError) as error:
            return JsonResponse({"detail": str(error)}, status=400)

        if game.table_state["status"] == "complete":
            game.status = GameSession.Status.COMPLETE
        await game.asave(update_fields=["status", "table_state", "updated_at"])

    snapshot = serialize_game(game)
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f"table-{game.id}",
        {"type": "table.snapshot", "payload": snapshot},
    )

    return JsonResponse(snapshot)
