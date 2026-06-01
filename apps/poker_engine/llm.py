import asyncio
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from apps.poker_engine.engine import legal_actions

POKER_ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["fold", "check", "call", "bet", "raise"],
            "description": "The poker action to take.",
        },
        "amount": {
            "type": "integer",
            "description": "Total target amount for bet/raise, exact call amount for call, or 0.",
        },
        "confidence": {
            "type": "number",
            "description": "Decision confidence from 0 to 1.",
        },
        "rationale": {
            "type": "string",
            "description": "Brief poker reasoning without revealing hidden information.",
        },
    },
    "required": ["action", "amount", "confidence", "rationale"],
    "additionalProperties": False,
}

PERSONALITY_PROMPTS = {
    "fish": "Loose-passive beginner. Over-calls, under-bluffs, and uses simple hand strength.",
    "tight": "Tight and cautious. Plays fewer hands and avoids marginal high-variance spots.",
    "tag": "Tight-aggressive regular. Applies pressure with playable ranges and value bets.",
    "pro": "Strong range-based player. Balances value, bluffs, blockers, pot odds, and position.",
}


class PokerLLMProvider(Protocol):
    async def choose_action(self, state: dict[str, Any], seat_id: int) -> dict[str, Any]:
        pass

    async def advise_hero(
        self,
        state: dict[str, Any],
        *,
        question: str,
        hero_seat: int = 0,
    ) -> str:
        pass


class LLMProviderUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class OpenAIResponsesPokerProvider:
    api_key: str
    model: str = "gpt-4.1-mini"
    timeout: float = 12.0
    base_url: str = "https://api.openai.com/v1"
    transport: Any | None = None

    async def choose_action(self, state: dict[str, Any], seat_id: int) -> dict[str, Any]:
        try:
            import httpx
        except ImportError as error:  # pragma: no cover - dependency health is checked separately.
            raise RuntimeError("httpx is required for OpenAI LLM opponents.") from error

        context = build_llm_decision_context(state, seat_id)
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You are a no-limit Texas Hold'em opponent. Choose one legal "
                                "action only. Use only the provided JSON context; do not assume "
                                "hidden cards, deck order, or other private player personalities."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(context, separators=(",", ":")),
                        }
                    ],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "poker_bot_action",
                    "strict": True,
                    "schema": POKER_ACTION_SCHEMA,
                }
            },
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            response = await client.post(
                f"{self.base_url.rstrip('/')}/responses",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

        return json.loads(_extract_response_text(response.json()))

    async def advise_hero(
        self,
        state: dict[str, Any],
        *,
        question: str,
        hero_seat: int = 0,
    ) -> str:
        try:
            import httpx
        except ImportError as error:  # pragma: no cover - dependency health is checked separately.
            raise RuntimeError("httpx is required for OpenAI LLM advice.") from error

        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You are a poker coach helping Hero make range-based decisions. "
                                "Use only the provided hero-visible context. Do not claim to know "
                                "hidden opponent cards, deck order, or private bot personalities."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(
                                {
                                    "question": question,
                                    "context": build_hero_advice_context(state, hero_seat),
                                },
                                separators=(",", ":"),
                            ),
                        }
                    ],
                },
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport) as client:
            response = await client.post(
                f"{self.base_url.rstrip('/')}/responses",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

        return _extract_response_text(response.json())


@dataclass(frozen=True)
class CodexCLIPokerProvider:
    command: str = "codex"
    model: str | None = None
    decision_timeout: float = 20.0
    max_decisions_per_advance: int = 1

    async def choose_action(self, state: dict[str, Any], seat_id: int) -> dict[str, Any]:
        context = build_llm_decision_context(state, seat_id)
        prompt = (
            "You are choosing one no-limit Texas Hold'em action for an opponent bot.\n"
            "Use only the JSON context below. Do not assume hidden cards, deck order, or other "
            "private personalities.\n"
            "Return exactly one JSON object matching this schema, with no markdown:\n"
            f"{json.dumps(POKER_ACTION_SCHEMA, separators=(',', ':'))}\n"
            "Poker context:\n"
            f"{json.dumps(context, separators=(',', ':'))}"
        )

        with tempfile.TemporaryDirectory(prefix="poker-codex-") as temp_dir:
            output_path = Path(temp_dir) / "decision.json"
            args = [
                self.command,
                "-a",
                "never",
                "exec",
                "--ephemeral",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--ignore-rules",
                "--output-last-message",
                str(output_path),
            ]
            if self.model:
                args.extend(["--model", self.model])
            args.append("-")

            process = await asyncio.create_subprocess_exec(
                *args,
                cwd=temp_dir,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate(prompt.encode())
            if process.returncode != 0:
                stderr_text = stderr.decode(errors="replace")[-500:]
                stdout_text = stdout.decode(errors="replace")[-500:]
                detail = stderr_text or stdout_text
                raise LLMProviderUnavailable(f"Codex CLI opponent failed: {detail.strip()}")

            try:
                return json.loads(output_path.read_text())
            except (OSError, json.JSONDecodeError):
                return _extract_json_object(stdout.decode(errors="replace"))

    async def advise_hero(
        self,
        state: dict[str, Any],
        *,
        question: str,
        hero_seat: int = 0,
    ) -> str:
        prompt = (
            "You are a poker coach helping Hero study no-limit Texas Hold'em.\n"
            "Use only the hero-visible JSON context. Do not claim to know hidden opponent cards, "
            "deck order, or private bot personalities. Discuss ranges, pot odds, bet sizing, "
            "position, and opponent tendencies inferred from public actions.\n"
            "Keep the answer concise and actionable.\n"
            f"Hero question: {question}\n"
            "Hero-visible context:\n"
            f"{json.dumps(build_hero_advice_context(state, hero_seat), separators=(',', ':'))}"
        )
        return await self._run_codex_text(prompt)

    async def _run_codex_text(self, prompt: str) -> str:
        with tempfile.TemporaryDirectory(prefix="poker-codex-") as temp_dir:
            output_path = Path(temp_dir) / "response.txt"
            args = [
                self.command,
                "-a",
                "never",
                "exec",
                "--ephemeral",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--ignore-rules",
                "--output-last-message",
                str(output_path),
            ]
            if self.model:
                args.extend(["--model", self.model])
            args.append("-")

            process = await asyncio.create_subprocess_exec(
                *args,
                cwd=temp_dir,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate(prompt.encode())
            if process.returncode != 0:
                stderr_text = stderr.decode(errors="replace")[-500:]
                stdout_text = stdout.decode(errors="replace")[-500:]
                detail = stderr_text or stdout_text
                raise LLMProviderUnavailable(f"Codex CLI coach failed: {detail.strip()}")

            try:
                answer = output_path.read_text().strip()
            except OSError:
                answer = stdout.decode(errors="replace").strip()
            if not answer:
                raise ValueError("Codex CLI coach returned an empty response.")
            return answer


def build_llm_decision_context(state: dict[str, Any], seat_id: int) -> dict[str, Any]:
    acting_seat = state["seats"][seat_id]
    personality = acting_seat.get("personality", "fish")
    return {
        "game": {
            "variant": state["variant"],
            "street": state["street"],
            "difficulty": state["difficulty"],
            "button_seat": state["button_seat"],
            "stakes": state["stakes"],
        },
        "acting_player": {
            "seat": acting_seat["seat"],
            "name": acting_seat["name"],
            "position": acting_seat["position"],
            "stack": acting_seat["stack"],
            "status": acting_seat["status"],
            "committed": acting_seat["committed"],
            "street_bet": acting_seat["street_bet"],
            "hole_cards": list(acting_seat["hole_cards"]),
            "personality": personality,
            "personality_brief": PERSONALITY_PROMPTS.get(
                personality,
                PERSONALITY_PROMPTS["fish"],
            ),
        },
        "table": {
            "community_cards": list(state["community_cards"]),
            "pot": state["pot"],
            "live_committed_pot": sum(seat["committed"] for seat in state["seats"]),
            "current_bet": state["current_bet"],
            "min_raise": state["min_raise"],
            "to_act": state["to_act"],
            "seats": [
                _visible_seat_for_llm(seat, reveal_hole_cards=seat["seat"] == seat_id)
                for seat in state["seats"]
            ],
        },
        "legal_actions": legal_actions(state),
        "hand_history": list(state["hand_history"]),
    }


def build_hero_advice_context(state: dict[str, Any], hero_seat: int = 0) -> dict[str, Any]:
    hero = state["seats"][hero_seat]
    return {
        "game": {
            "variant": state["variant"],
            "street": state["street"],
            "difficulty": state["difficulty"],
            "button_seat": state["button_seat"],
            "stakes": state["stakes"],
            "status": state["status"],
        },
        "hero": {
            "seat": hero["seat"],
            "position": hero["position"],
            "stack": hero["stack"],
            "status": hero["status"],
            "committed": hero["committed"],
            "street_bet": hero["street_bet"],
            "hole_cards": list(hero["hole_cards"]),
        },
        "table": {
            "community_cards": list(state["community_cards"]),
            "pot": state["pot"],
            "live_committed_pot": sum(seat["committed"] for seat in state["seats"]),
            "current_bet": state["current_bet"],
            "min_raise": state["min_raise"],
            "to_act": state["to_act"],
            "seats": [
                _visible_seat_for_llm(seat, reveal_hole_cards=seat["seat"] == hero_seat)
                for seat in state["seats"]
            ],
        },
        "legal_actions": legal_actions(state) if state.get("to_act") == hero_seat else [],
        "hand_history": list(state["hand_history"]),
        "winners": list(state.get("winners", [])),
    }


def validate_llm_decision(
    decision: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any] | None:
    if not isinstance(decision, dict):
        return None

    action_name = str(decision.get("action", "")).lower()
    available = {action["action"]: action for action in legal_actions(state)}
    action = available.get(action_name)
    if action is None:
        return None

    if action_name in {"fold", "check"}:
        return {"action": action_name}
    if action_name == "call":
        return {"action": "call", "amount": action["amount"]}

    try:
        amount = int(decision.get("amount"))
    except (TypeError, ValueError):
        return None

    if action["min_amount"] <= amount <= action["max_amount"]:
        return {"action": action_name, "amount": amount}
    return None


def load_openai_api_key(auth_path: str | Path | None = None) -> str | None:
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key

    path = Path(auth_path) if auth_path else Path.home() / ".codex" / "auth.json"
    try:
        with path.expanduser().open() as auth_file:
            auth_data = json.load(auth_file)
    except (OSError, json.JSONDecodeError):
        return None

    key = auth_data.get("OPENAI_API_KEY")
    if isinstance(key, str) and key:
        return key

    tokens = auth_data.get("tokens")
    if isinstance(tokens, dict):
        access_token = tokens.get("access_token")
        if isinstance(access_token, str) and access_token:
            return access_token

    return None


def has_codex_auth(auth_path: str | Path | None = None) -> bool:
    path = Path(auth_path) if auth_path else Path.home() / ".codex" / "auth.json"
    try:
        with path.expanduser().open() as auth_file:
            auth_data = json.load(auth_file)
    except (OSError, json.JSONDecodeError):
        return False

    tokens = auth_data.get("tokens")
    return isinstance(tokens, dict) and isinstance(tokens.get("access_token"), str)


def _visible_seat_for_llm(seat: dict[str, Any], *, reveal_hole_cards: bool) -> dict[str, Any]:
    return {
        "seat": seat["seat"],
        "name": seat["name"],
        "role": seat["role"],
        "position": seat["position"],
        "stack": seat["stack"],
        "status": seat["status"],
        "committed": seat["committed"],
        "street_bet": seat["street_bet"],
        "hole_cards": list(seat["hole_cards"]) if reveal_hole_cards else [],
    }


def _extract_response_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]

    chunks: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str) and content.get("type") in {"output_text", "text"}:
                chunks.append(text)
    if chunks:
        return "".join(chunks)

    raise ValueError("OpenAI response did not include output text.")


def _extract_json_object(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise ValueError("Codex CLI response did not include a JSON object.")
