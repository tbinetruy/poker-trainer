import type { Difficulty, GameSession } from "@/lib/types"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"

export async function createGame(difficulty: Difficulty, llmBots = false): Promise<GameSession> {
  const response = await fetch(`${API_BASE_URL}/api/games/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ difficulty, llm_bots: llmBots }),
  })

  if (!response.ok) {
    throw new Error(`Failed to create game: ${await responseErrorDetail(response)}`)
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
    throw new Error(`Failed to apply action: ${await responseErrorDetail(response)}`)
  }

  return response.json()
}

async function responseErrorDetail(response: Response) {
  try {
    const payload = await response.json()
    if (typeof payload.detail === "string") {
      return payload.detail
    }
  } catch {
    // Fall back to the status code below.
  }

  return String(response.status)
}
