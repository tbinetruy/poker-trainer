# Poker Trainer

A web-based Texas Hold'em training app with a Django/Channels backend and React frontend.

## Milestone 1

This first milestone establishes the app shell:

- Async-capable Django backend.
- Django Channels routing for table updates.
- React + TypeScript frontend.
- Tailwind + shadcn-style local UI components.
- Basic start-game and table shell flow.

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

