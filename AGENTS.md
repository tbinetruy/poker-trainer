# Poker Trainer

## Product Direction

Build a web-based Texas Hold'em trainer for learning modern range-based poker, bet sizing, table reads, and post-session review.

Core principles:
- The poker simulator is deterministic and authoritative.
- LLMs never own game legality, pot accounting, deck state, or showdown resolution.
- Any LLM opponent or coach receives only the information that role is allowed to know.
- Bot personalities are private during play; coaches may infer tendencies only from observable actions.

## Stack Decisions

- Backend: Django with async-capable views where external LLM calls may happen.
- Realtime: use Django Channels from the start for table state updates, player actions, and coach chat.
- Frontend: React + TypeScript.
- Components: use shadcn/ui when possible, backed by Tailwind and lucide-react icons.
- API style: prefer explicit JSON contracts and serializers for all state crossing the backend/frontend boundary.

## Backend Guidance

- Keep game state mutations in deterministic services/state machines, not views or consumers.
- Views and Channels consumers orchestrate requests, validate inputs, call services, and serialize results.
- Use async views/consumers for endpoints that may call LLM providers or wait on network I/O.
- Do not hold a database transaction open while awaiting an LLM response.
- Validate LLM-selected actions against legal actions before applying them.
- Record full hand histories, including public action history and private audit metadata for post-game review.

## LLM Privacy Boundaries

LLM opponents may receive:
- Their own hole cards.
- Public board cards.
- Stack sizes, position, pot size, current bet, legal actions.
- Betting/action history visible to that player.
- Their private personality prompt.

LLM opponents must not receive:
- Other players' hole cards.
- Deck order or future board cards.
- Hidden bot personalities.
- Simulator internals that imply hidden information.

In-hand AI coach may receive only hero-visible information. Post-game review may use privileged data only when clearly labeled as post-game analysis.

## Local Skills

Project skills live in `.codex/skills/`.

Use the Django skills for backend modeling, testing, debugging, and quality checks. Use the React skills for component structure, data fetching, forms, tables, and shadcn/ui conventions.

