import json
import uuid
from asyncio import Lock, create_task, sleep

from channels.layers import get_channel_layer
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from apps.poker_engine import apply_action
from apps.poker_engine.bots import advance_bots_until_human_turn_async
from apps.poker_engine.engine import InvalidAction, annotate_latest_player_action
from apps.poker_engine.llm import LLMProviderUnavailable
from apps.tables.llm import get_default_llm_provider
from apps.tables.models import GameSession
from apps.tables.selectors import serialize_game, serialize_game_review
from apps.tables.services import build_dealt_table_state, build_initial_table_state_async

_ACTION_LOCKS: dict[str, Lock] = {}


async def _save_and_broadcast_table_state(game: GameSession, table_state: dict) -> None:
    game.table_state = table_state
    await _save_and_broadcast_game(game)


async def _save_and_broadcast_game(game: GameSession) -> None:
    if game.table_state["status"] == "complete":
        game.status = GameSession.Status.COMPLETE
    await game.asave(update_fields=["status", "table_state", "updated_at"])
    await _broadcast_game_snapshot(game)


async def _broadcast_game_snapshot(game: GameSession) -> None:
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f"table-{game.id}",
        {"type": "table.snapshot", "payload": serialize_game(game)},
    )


async def _broadcast_table_thinking(game_id, seat_id: int | None) -> None:
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        f"table-{game_id}",
        {"type": "table.thinking", "payload": {"seat": seat_id}},
    )


def _schedule_bot_advance(game_id, llm_provider) -> None:
    create_task(_advance_game_bots(game_id, llm_provider))


async def _advance_game_bots(game_id, llm_provider, *, startup_delay: float = 0.05) -> None:
    if startup_delay > 0:
        await sleep(startup_delay)

    lock = _ACTION_LOCKS.setdefault(str(game_id), Lock())
    async with lock:
        try:
            game = await GameSession.objects.aget(id=game_id)
        except GameSession.DoesNotExist:
            return

        if game.table_state.get("status") == "complete" or game.table_state.get("to_act") == 0:
            return

        try:
            game.table_state = await advance_bots_until_human_turn_async(
                game.table_state,
                llm_provider=llm_provider,
                on_thinking=lambda thinking_seat: _broadcast_table_thinking(
                    game.id,
                    thinking_seat,
                ),
                on_update=lambda table_state: _save_and_broadcast_table_state(
                    game,
                    table_state,
                ),
            )
        except LLMProviderUnavailable as error:
            game.table_state.setdefault("llm_bot_errors", []).append(
                {"seat": game.table_state.get("to_act"), "error": str(error)}
            )
            await _save_and_broadcast_game(game)


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
    llm_bots_enabled = bool(payload.get("llm_bots") or payload.get("llmBots"))

    game_id = uuid.uuid4()
    llm_provider = get_default_llm_provider() if llm_bots_enabled else None
    if llm_bots_enabled and llm_provider is None:
        return JsonResponse({"detail": "LLM opponents are not configured."}, status=503)
    button_seat = await GameSession.objects.acount() % 5
    try:
        if llm_bots_enabled:
            table_state = build_dealt_table_state(
                difficulty,
                seed=str(game_id),
                llm_bots_enabled=True,
                button_seat=button_seat,
            )
        else:
            table_state = await build_initial_table_state_async(
                difficulty,
                seed=str(game_id),
                llm_bots_enabled=False,
                button_seat=button_seat,
            )
    except LLMProviderUnavailable as error:
        return JsonResponse({"detail": str(error)}, status=503)
    game = await GameSession.objects.acreate(
        id=game_id,
        difficulty=difficulty,
        status=GameSession.Status.ACTIVE,
        table_state=table_state,
    )
    if llm_bots_enabled:
        _schedule_bot_advance(game.id, llm_provider)
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
            annotate_latest_player_action(game.table_state, seat_id=seat_id, source="human")
            await _save_and_broadcast_game(game)
            llm_provider = (
                get_default_llm_provider() if game.table_state.get("llm_bots_enabled") else None
            )
            game.table_state = await advance_bots_until_human_turn_async(
                game.table_state,
                llm_provider=llm_provider,
                on_thinking=lambda thinking_seat: _broadcast_table_thinking(
                    game.id,
                    thinking_seat,
                ),
                on_update=lambda table_state: _save_and_broadcast_table_state(
                    game,
                    table_state,
                ),
            )
        except LLMProviderUnavailable as error:
            return JsonResponse({"detail": str(error)}, status=503)
        except (InvalidAction, TypeError, ValueError) as error:
            return JsonResponse({"detail": str(error)}, status=400)

    snapshot = serialize_game(game)

    return JsonResponse(snapshot)


@csrf_exempt
async def game_review(request: HttpRequest, game_id) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    lock = _ACTION_LOCKS.setdefault(str(game_id), Lock())
    async with lock:
        try:
            game = await GameSession.objects.aget(id=game_id)
        except GameSession.DoesNotExist:
            return JsonResponse({"detail": "Not found."}, status=404)

        if game.table_state.get("status") != "complete":
            return JsonResponse(
                {"detail": "Review is available after the hand is complete."}, status=409
            )

        game.table_state["private_review_revealed"] = True
        await game.asave(update_fields=["table_state", "updated_at"])

    return JsonResponse(serialize_game_review(game))


@csrf_exempt
async def game_advice(request: HttpRequest, game_id) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Malformed JSON."}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({"detail": "JSON body must be an object."}, status=400)

    question = str(payload.get("question", "")).strip()
    if not question:
        return JsonResponse({"detail": "Question is required."}, status=400)
    if len(question) > 1_000:
        return JsonResponse({"detail": "Question is too long."}, status=400)
    include_private_review = bool(
        payload.get("include_private_review") or payload.get("includePrivateReview")
    )

    try:
        game = await GameSession.objects.aget(id=game_id)
    except GameSession.DoesNotExist:
        return JsonResponse({"detail": "Not found."}, status=404)

    if include_private_review:
        if game.table_state.get("status") != "complete":
            return JsonResponse(
                {"detail": "Private review is available after the hand is complete."}, status=409
            )
        if not game.table_state.get("private_review_revealed"):
            return JsonResponse(
                {"detail": "Private review must be revealed before asking the coach."}, status=409
            )

    provider = get_default_llm_provider()
    if provider is None:
        return JsonResponse({"detail": "AI coach is not configured."}, status=503)

    try:
        answer = await provider.advise_hero(
            game.table_state,
            question=question,
            hero_seat=0,
            include_private_review=include_private_review,
        )
    except LLMProviderUnavailable as error:
        return JsonResponse({"detail": str(error)}, status=503)

    return JsonResponse({"answer": answer})
