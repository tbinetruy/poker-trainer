import { Bot, Brain, Radio, Spade, ToggleRight, Users } from "lucide-react"
import { useState } from "react"

import { applyGameAction, askCoach, createGame } from "@/lib/api"
import type { Difficulty, GameSession, LegalAction } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const difficulties: Array<{ value: Difficulty; label: string; detail: string }> = [
  { value: "beginner", label: "Beginner", detail: "Mostly loose and passive opponents" },
  { value: "medium", label: "Medium", detail: "Mixed table with one sharper player" },
  { value: "advanced", label: "Advanced", detail: "Tougher table, fewer obvious leaks" },
]

function App() {
  const [difficulty, setDifficulty] = useState<Difficulty>("beginner")
  const [llmBots, setLlmBots] = useState(false)
  const [game, setGame] = useState<GameSession | null>(null)
  const [actionAmounts, setActionAmounts] = useState<Record<string, number>>({})
  const [coachMessages, setCoachMessages] = useState<Array<{ role: "hero" | "coach"; text: string }>>([])
  const [coachQuestion, setCoachQuestion] = useState("")
  const [isStarting, setIsStarting] = useState(false)
  const [isActing, setIsActing] = useState(false)
  const [isAskingCoach, setIsAskingCoach] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)

  const startGame = async () => {
    setIsStarting(true)
    setStartError(null)
    try {
      const nextGame = await createGame(difficulty, llmBots)
      setGame(nextGame)
      setCoachMessages([])
      setCoachQuestion("")
    } catch (error) {
      setStartError(error instanceof Error ? error.message : "Failed to start game.")
    } finally {
      setIsStarting(false)
    }
  }

  const submitAction = async (legalAction: LegalAction, amountOverride?: number) => {
    if (!game) {
      return
    }

    setIsActing(true)
    setStartError(null)
    try {
      const amount =
        amountOverride ??
        ("amount" in legalAction
          ? legalAction.amount
          : "min_amount" in legalAction
            ? legalAction.min_amount
            : undefined)
      setGame(await applyGameAction(game.id, { seat: 0, action: legalAction.action, amount }))
    } catch (error) {
      setStartError(error instanceof Error ? error.message : "Failed to apply action.")
    } finally {
      setIsActing(false)
    }
  }

  const submitCoachQuestion = async () => {
    if (!game || !coachQuestion.trim()) {
      return
    }

    const question = coachQuestion.trim()
    setCoachQuestion("")
    setCoachMessages((messages) => [...messages, { role: "hero", text: question }])
    setIsAskingCoach(true)
    setStartError(null)
    try {
      const response = await askCoach(game.id, question)
      setCoachMessages((messages) => [...messages, { role: "coach", text: response.answer }])
    } catch (error) {
      setStartError(error instanceof Error ? error.message : "Failed to ask coach.")
    } finally {
      setIsAskingCoach(false)
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-5 py-6 lg:px-8">
        <header className="flex flex-col gap-4 border-b border-border pb-5 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="mb-3 flex items-center gap-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <Spade className="h-5 w-5" />
              </span>
              <Badge variant="secondary">Milestone 4</Badge>
            </div>
            <h1 className="text-3xl font-semibold tracking-normal md:text-4xl">Poker Trainer</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
              Deterministic Hold'em with private bot personalities, optional LLM opponents, and
              Channels wired for realtime table updates.
            </p>
          </div>
          <Button onClick={startGame} disabled={isStarting}>
            {isStarting ? "Starting..." : "Start game"}
          </Button>
        </header>

        {startError ? (
          <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
            {startError}
          </div>
        ) : null}

        <section className="grid gap-4">
          <aside className="grid gap-3 lg:grid-cols-[2fr_1fr_1fr]">
            <Card>
              <CardHeader>
                <CardTitle>Table Strength</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-2 md:grid-cols-3">
                {difficulties.map((option) => (
                  <button
                    className={`w-full rounded-md border p-3 text-left transition ${
                      difficulty === option.value
                        ? "border-primary bg-primary/8"
                        : "border-border bg-card hover:bg-accent"
                    }`}
                    key={option.value}
                    onClick={() => setDifficulty(option.value)}
                    type="button"
                  >
                    <span className="block text-sm font-medium">{option.label}</span>
                    <span className="mt-1 block text-xs leading-5 text-muted-foreground">
                      {option.detail}
                    </span>
                  </button>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Realtime</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3 text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <Radio className="h-4 w-4 text-primary" />
                  <code className="text-foreground">/ws/tables/:id/</code>
                </div>
                <div className="flex items-center gap-2">
                  <Brain className="h-4 w-4 text-primary" />
                  Redacted LLM context.
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Opponent Engine</CardTitle>
              </CardHeader>
              <CardContent>
                <label className="flex cursor-pointer items-center justify-between gap-3 rounded-md border border-border p-3 text-sm">
                  <span className="flex items-center gap-2">
                    <ToggleRight className="h-4 w-4 text-primary" />
                    LLM opponents
                  </span>
                  <input
                    checked={llmBots}
                    className="h-4 w-4 accent-primary"
                    onChange={(event) => setLlmBots(event.target.checked)}
                    type="checkbox"
                  />
                </label>
              </CardContent>
            </Card>
          </aside>

          <section className="rounded-lg border border-border bg-card p-4">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Table</h2>
                <p className="text-sm text-muted-foreground">
                  {game
                    ? `${game.table_state.street} · to act: ${
                        game.table_state.to_act ?? "none"
                      } · ${game.table_state.llm_bots_enabled ? "LLM bots" : "rule bots"} · Game ${game.id}`
                    : "Start a game to create a table session."}
                </p>
              </div>
              <Badge>{game?.status ?? "idle"}</Badge>
            </div>

            <div className="min-h-[420px] rounded-md bg-[radial-gradient(circle_at_center,hsl(156_42%_28%),hsl(156_45%_16%))] p-5 text-white">
              <div className="grid gap-3 md:grid-cols-5">
                {(game?.table_state.seats ?? []).map((seat) => (
                  <SeatPanel key={seat.seat} seat={seat} />
                ))}
              </div>
              <div className="mt-4 rounded-md border border-white/15 bg-black/25 p-3">
                <div className="mb-2 text-xs font-semibold uppercase text-white/60">Bet History</div>
                <div className="grid gap-2 text-sm text-white/75 md:grid-cols-2 xl:grid-cols-3">
                  {(game?.table_state.hand_history ?? []).slice(-6).map((event, index) => (
                    <div
                      className="flex justify-between gap-3 rounded border border-white/10 bg-black/20 px-2 py-1"
                      key={`compact-${index}-${event.action}`}
                    >
                      <span className="truncate">{game ? historyLabel(game, event) : ""}</span>
                      <span>{historyAmount(event)}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="mt-6 grid gap-4 rounded-md border border-white/15 bg-black/15 p-4 lg:grid-cols-[1fr_320px]">
                <div className="w-64 rounded-md border border-white/15 bg-black/25 p-4 text-center">
                  <div className="text-xs uppercase text-white/60">Pot</div>
                  <div className="text-3xl font-semibold">{game?.table_state.pot ?? 0}</div>
                  <div className="mt-4 flex min-h-9 justify-center gap-1">
                    {(game?.table_state.community_cards ?? []).map((card) => (
                      <span
                        className="rounded bg-white px-2 py-1 text-sm font-semibold text-slate-950"
                        key={card}
                      >
                        {card}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="rounded-md border border-white/15 bg-black/25 p-3">
                  <div className="text-xs font-semibold uppercase text-white/60">Bet History</div>
                  <div className="mt-2 max-h-40 space-y-1 overflow-auto text-sm text-white/75">
                    {(game?.table_state.hand_history ?? []).map((event, index) => (
                      <div className="flex justify-between gap-3" key={`${index}-${event.action}`}>
                        <span>{game ? historyLabel(game, event) : ""}</span>
                        <span>{historyAmount(event)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {game ? (
              <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div className="text-sm text-muted-foreground">
                  {game.table_state.status === "complete" ? "Hand finished" : "Hero action"}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {game.table_state.status === "complete" ? (
                    <span className="text-sm text-muted-foreground">
                      Hand complete{winnerText(game)}.
                    </span>
                  ) : game.table_state.to_act === 0 ? (
                    game.table_state.legal_actions.map((legalAction) => {
                      if ("min_amount" in legalAction) {
                        const amount = actionAmounts[legalAction.action] ?? legalAction.min_amount
                        return (
                          <div
                            className="flex items-center gap-2 rounded-md border border-border bg-background p-1"
                            key={legalAction.action}
                          >
                            <input
                              className="h-8 w-24 rounded border border-border bg-card px-2 text-sm"
                              max={legalAction.max_amount}
                              min={legalAction.min_amount}
                              onChange={(event) =>
                                setActionAmounts((current) => ({
                                  ...current,
                                  [legalAction.action]: Number(event.target.value),
                                }))
                              }
                              step={game.table_state.stakes.big_blind}
                              type="number"
                              value={amount}
                            />
                            <Button
                              disabled={isActing}
                              onClick={() => submitAction(legalAction, amount)}
                              size="sm"
                            >
                              {legalAction.action}
                            </Button>
                          </div>
                        )
                      }

                      return (
                        <Button
                          disabled={isActing}
                          key={legalAction.action}
                          onClick={() => submitAction(legalAction)}
                          size="sm"
                          variant={legalAction.action === "fold" ? "outline" : "default"}
                        >
                          {actionLabel(legalAction)}
                        </Button>
                      )
                    })
                  ) : (
                    <span className="text-sm text-muted-foreground">
                      Waiting for simulator/bot action.
                    </span>
                  )}
                </div>
              </div>
            ) : null}

            {game ? (
              <div className="mt-4 grid gap-3 md:grid-cols-[1fr_280px]">
                <div className="rounded-md border border-border bg-background p-3">
                  <h3 className="text-sm font-medium">Bet History</h3>
                  <div className="mt-2 max-h-44 space-y-1 overflow-auto text-sm text-muted-foreground">
                    {game.table_state.hand_history.map((event, index) => (
                      <div className="flex justify-between gap-3" key={`${index}-${event.action}`}>
                        <span>{historyLabel(game, event)}</span>
                        <span>{historyAmount(event)}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="rounded-md border border-border bg-background p-3">
                  <h3 className="text-sm font-medium">Betting</h3>
                  <div className="mt-2 space-y-1 text-sm text-muted-foreground">
                    <div className="flex justify-between">
                      <span>Current bet</span>
                      <span>{game.table_state.current_bet.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Minimum raise</span>
                      <span>{game.table_state.min_raise.toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : null}

            {game ? (
              <div className="mt-4 rounded-md border border-border bg-background p-4">
                <h3 className="text-base font-medium">AI Coach</h3>
                <div className="mt-3 min-h-72 max-h-[520px] space-y-3 overflow-auto rounded-md border border-border bg-card p-3 text-sm">
                  {coachMessages.length === 0 ? (
                    <p className="text-muted-foreground">
                      Ask about ranges, sizing, pot odds, or opponent tendencies.
                    </p>
                  ) : (
                    coachMessages.map((message, index) => (
                      <div
                        className={`max-w-[860px] rounded-md px-4 py-3 leading-6 ${
                          message.role === "coach"
                            ? "bg-muted text-foreground"
                            : "ml-auto bg-primary text-primary-foreground"
                        }`}
                        key={`${message.role}-${index}`}
                      >
                        {message.role === "coach" ? (
                          <MarkdownText text={message.text} />
                        ) : (
                          message.text
                        )}
                      </div>
                    ))
                  )}
                </div>
                <div className="mt-3 flex gap-2">
                  <input
                    className="min-w-0 flex-1 rounded-md border border-input bg-card px-3 py-2 text-sm"
                    disabled={isAskingCoach}
                    onChange={(event) => setCoachQuestion(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        void submitCoachQuestion()
                      }
                    }}
                    placeholder="Ask the coach..."
                    value={coachQuestion}
                  />
                  <Button
                    disabled={isAskingCoach || !coachQuestion.trim()}
                    onClick={submitCoachQuestion}
                    size="sm"
                  >
                    {isAskingCoach ? "Asking..." : "Ask"}
                  </Button>
                </div>
              </div>
            ) : null}
          </section>
        </section>
      </div>
    </main>
  )
}

function actionLabel(action: LegalAction) {
  if ("amount" in action) {
    return `${action.action} ${action.amount}`
  }
  if ("min_amount" in action) {
    return `${action.action} ${action.min_amount}`
  }
  return action.action
}

function winnerText(game: GameSession) {
  const winners = game.table_state.winners
  if (winners.length === 0) {
    return ""
  }

  return `: ${winners
    .map((winner) => {
      const seat = game.table_state.seats.find((item) => item.seat === winner.seat)
      return `${seat?.name ?? `Seat ${winner.seat}`} wins ${winner.amount}`
    })
    .join(", ")}`
}

function SeatPanel({ seat }: { seat: GameSession["table_state"]["seats"][number] }) {
  return (
    <div className="rounded-md border border-white/15 bg-black/30 p-3 text-center shadow-lg">
      <div className="mb-2 flex items-center justify-center gap-1">
        {seat.role === "human" ? <Users className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        <Badge variant={positionBadgeVariant(seat.position)}>{seat.position}</Badge>
      </div>
      <div className="truncate text-sm font-medium">{seat.name}</div>
      <div className="text-xs text-white/70">{seat.stack.toLocaleString()}</div>
      {seat.hole_cards.length > 0 ? (
        <div className="mt-2 flex h-8 justify-center gap-1">
          {seat.hole_cards.map((card) => (
            <span
              className="rounded bg-white px-2 py-1 text-sm font-semibold text-slate-950"
              key={card}
            >
              {card}
            </span>
          ))}
        </div>
      ) : (
        <div className="mt-2 h-8" />
      )}
      <div className="mt-2 grid grid-cols-2 gap-1 text-xs text-white/75">
        <span>Bet {seat.street_bet.toLocaleString()}</span>
        <span>In {seat.committed.toLocaleString()}</span>
      </div>
      <Badge className="mt-2" variant={seat.status === "active" ? "secondary" : "outline"}>
        {seat.status}
      </Badge>
    </div>
  )
}

function historyLabel(game: GameSession, event: Record<string, unknown>) {
  const seatId = typeof event.seat === "number" ? event.seat : null
  const seat = seatId === null ? null : game.table_state.seats.find((item) => item.seat === seatId)
  const actor = seat?.name ?? "Dealer"
  return `${String(event.street)} · ${actor} ${formatAction(String(event.action))}`
}

function historyAmount(event: Record<string, unknown>) {
  if (typeof event.total === "number") {
    return `to ${event.total.toLocaleString()}`
  }
  if (typeof event.amount === "number") {
    return event.amount.toLocaleString()
  }
  return ""
}

function formatAction(action: string) {
  return action.replaceAll("_", " ")
}

function positionBadgeVariant(position: string): "default" | "secondary" {
  return position === "BTN" || position === "SB" || position === "BB" ? "default" : "secondary"
}

function MarkdownText({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/).filter(Boolean)

  return (
    <div className="space-y-3">
      {blocks.map((block, index) => {
        const lines = block.split("\n").filter(Boolean)
        const isList = lines.every((line) => /^[-*]\s+/.test(line.trim()))
        if (isList) {
          return (
            <ul className="list-disc space-y-1 pl-5" key={index}>
              {lines.map((line, lineIndex) => (
                <li key={lineIndex}>{renderInlineMarkdown(line.replace(/^[-*]\s+/, ""))}</li>
              ))}
            </ul>
          )
        }

        return <p key={index}>{renderInlineMarkdown(lines.join(" "))}</p>
      })}
    </div>
  )
}

function renderInlineMarkdown(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g)

  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code className="rounded bg-background px-1 py-0.5 text-[0.92em]" key={index}>
          {part.slice(1, -1)}
        </code>
      )
    }
    return part
  })
}

export default App
