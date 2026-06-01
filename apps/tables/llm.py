from django.conf import settings

from apps.poker_engine.llm import (
    CodexCLIPokerProvider,
    OpenAIResponsesPokerProvider,
    has_codex_auth,
    load_openai_api_key,
)


def get_default_llm_provider() -> OpenAIResponsesPokerProvider | CodexCLIPokerProvider | None:
    provider = settings.POKER_LLM_PROVIDER
    auth_path = getattr(settings, "POKER_OPENAI_AUTH_PATH", None)
    if provider == "codex_cli":
        if not has_codex_auth(auth_path):
            return None
        return CodexCLIPokerProvider(
            command=settings.POKER_CODEX_COMMAND,
            model=settings.POKER_CODEX_MODEL,
            decision_timeout=settings.POKER_CODEX_TIMEOUT,
        )

    api_key = load_openai_api_key(auth_path)
    if not api_key:
        return None

    return OpenAIResponsesPokerProvider(
        api_key=api_key,
        model=settings.POKER_OPENAI_MODEL,
        timeout=settings.POKER_OPENAI_TIMEOUT,
    )
