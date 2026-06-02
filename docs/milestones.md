# Milestones

## 1. Boilerplate

- Django project with async-ready configuration.
- Django Channels configured from the start.
- React + TypeScript frontend.
- Tailwind + shadcn/ui component setup.
- Basic start-game/table shell.

## 2. Deterministic Poker Simulator

- Texas Hold'em hand state machine.
- Legal actions, blinds, streets, pot accounting, and showdown.
- Full hand history JSON.
- Tests for betting rounds, legal actions, pots, and hand resolution.

## 3. Bot Framework

- Pluggable bot strategy interface.
- Random/rule-based baseline bots.
- Private personality assignment.
- Difficulty presets that choose personality pools globally, not per visible player label.

## 4. LLM Opponents

- Provider abstraction for OpenAI-compatible models.
- Strict visible-state serializer per acting player.
- Structured JSON action responses.
- Backend legality validation and deterministic fallback for invalid LLM actions.
- Calibrated pro archetypes (`pro_tag`, `pro_lag`, `pro_exploit`, `pro_balanced`) for
  stronger, more varied advanced tables.
- Decision-process guardrails for LLM opponents covering pot odds, SPR, multiway
  discipline, river bluff-catching, and exploitative adjustments.
- Action-source audit trail showing human actions, LLM decisions, and deterministic
  fallback reasons.
- Realtime table updates while LLM opponents think and act, including per-seat thinking
  indicators and intermediate snapshots after each action.

## 5. In-Hand AI Coach

- Channels-backed coach chat.
- Coach sees only hero-visible state during the hand.
- Coach can discuss ranges, pot odds, sizing, and inferred opponent tendencies.
- Coach suggestions must reference current legal actions.

## 6. Post-Game Review

- Session summary and per-hand analysis.
- Feedback on good decisions, leaks, ranges, sizing, and opponent reads.
- Optional privileged review comparing inferred personalities against actual bot personalities.

## 7. Training Tools

- Spot replay from decision points.
- Fold-flow modal to choose whether to stop the hand, continue with LLM opponents, or
  reveal immediately.
- Pot odds and sizing helpers.
- Range/equity visualizations.
- Filters for common study spots.
