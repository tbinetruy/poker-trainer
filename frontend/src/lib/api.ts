import type { Difficulty, GameSession } from "@/lib/types"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"

export async function createGame(difficulty: Difficulty): Promise<GameSession> {
  const response = await fetch(`${API_BASE_URL}/api/games/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ difficulty }),
  })

  if (!response.ok) {
    throw new Error(`Failed to create game: ${response.status}`)
  }

  return response.json()
}

export async function applyGameAction(
  gameId: string,
  payload: { seat: number; action: string; amount?: number },
): Promise<GameSession> {
  const response = await fetch(`${API_BASE_URL}/api/games/${gameId}/actions/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(`Failed to apply action: ${response.status}`)
  }

  return response.json()
}
