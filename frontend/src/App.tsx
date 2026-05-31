import { Bot, Brain, Radio, Spade, Users } from "lucide-react"
import { useState } from "react"

import { createGame } from "@/lib/api"
import type { Difficulty, GameSession } from "@/lib/types"
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
  const [game, setGame] = useState<GameSession | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)

  const startGame = async () => {
    setIsStarting(true)
    setStartError(null)
    try {
      setGame(await createGame(difficulty))
    } catch (error) {
      setStartError(error instanceof Error ? error.message : "Failed to start game.")
    } finally {
      setIsStarting(false)
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
              <Badge variant="secondary">Milestone 1</Badge>
            </div>
            <h1 className="text-3xl font-semibold tracking-normal md:text-4xl">Poker Trainer</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
              Deterministic table shell with private bot personalities, async-ready Django, and
              Channels wired for realtime play.
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

        <section className="grid gap-4 lg:grid-cols-[320px_1fr]">
          <aside className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Table Strength</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
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
              <CardContent className="space-y-3 text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <Radio className="h-4 w-4 text-primary" />
                  Channels route: <code className="text-foreground">/ws/tables/:id/</code>
                </div>
                <div className="flex items-center gap-2">
                  <Brain className="h-4 w-4 text-primary" />
                  Async views are ready for future LLM calls.
                </div>
              </CardContent>
            </Card>
          </aside>

          <section className="rounded-lg border border-border bg-card p-4">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Table</h2>
                <p className="text-sm text-muted-foreground">
                  {game ? `Game ${game.id}` : "Start a game to create a table session."}
                </p>
              </div>
              <Badge>{game?.status ?? "idle"}</Badge>
            </div>

            <div className="grid min-h-[420px] place-items-center rounded-md bg-[radial-gradient(circle_at_center,hsl(156_42%_28%),hsl(156_45%_16%))] p-6 text-white">
              <div className="relative h-[320px] w-full max-w-[720px] rounded-[48%] border border-white/20 bg-emerald-950/40 shadow-2xl">
                {(game?.table_state.seats ?? []).map((seat) => (
                  <div
                    className="absolute w-32 rounded-md border border-white/15 bg-black/35 p-3 text-center shadow-lg backdrop-blur"
                    key={seat.seat}
                    style={seatPosition(seat.seat)}
                  >
                    <div className="mb-1 flex justify-center">
                      {seat.role === "human" ? (
                        <Users className="h-4 w-4" />
                      ) : (
                        <Bot className="h-4 w-4" />
                      )}
                    </div>
                    <div className="truncate text-sm font-medium">{seat.name}</div>
                    <div className="text-xs text-white/70">
                      {seat.position} · {seat.stack.toLocaleString()}
                    </div>
                  </div>
                ))}
                <div className="absolute left-1/2 top-1/2 w-44 -translate-x-1/2 -translate-y-1/2 rounded-md border border-white/15 bg-black/25 p-4 text-center">
                  <div className="text-xs uppercase text-white/60">Pot</div>
                  <div className="text-2xl font-semibold">{game?.table_state.pot ?? 0}</div>
                </div>
              </div>
            </div>
          </section>
        </section>
      </div>
    </main>
  )
}

function seatPosition(seat: number) {
  const positions = [
    { left: "50%", bottom: "-28px", transform: "translateX(-50%)" },
    { right: "-18px", bottom: "74px" },
    { right: "18px", top: "24px" },
    { left: "18px", top: "24px" },
    { left: "-18px", bottom: "74px" },
  ]

  return positions[seat] ?? positions[0]
}

export default App
