# Poker Trainer

A web-based Texas Hold'em training app with a Django/Channels backend and React frontend.

## Milestone 1

This first milestone establishes the app shell:

- Async-capable Django backend.
- Django Channels routing for table updates.
- React + TypeScript frontend.
- Tailwind + shadcn-style local UI components.
- Basic start-game and table shell flow.

## Milestone 4

LLM opponents can be enabled per game from the frontend. By default, local development uses
`codex exec` with the Codex bearer token in `~/.codex/auth.json`; set
`POKER_LLM_PROVIDER=openai` to use the OpenAI Responses API with `OPENAI_API_KEY`. Bot prompts
only include the acting bot's private cards/personality plus public table state, legal actions,
and public betting history; returned actions are validated by the deterministic engine before
being applied.

Optional settings:

```bash
export POKER_OPENAI_MODEL=gpt-4.1-mini
export POKER_OPENAI_TIMEOUT=12
export POKER_OPENAI_AUTH_PATH=~/.codex/auth.json
export POKER_LLM_PROVIDER=codex_cli
export POKER_CODEX_TIMEOUT=45
```

## Development

Backend:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
python manage.py migrate
python manage.py runserver
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the backend at `http://localhost:8000`.
