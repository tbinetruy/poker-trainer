import { useEffect } from "react"

import { tableWebSocketUrl } from "@/lib/api"
import type { GameSession } from "@/lib/types"

type TableSocketMessage =
  | { type: "table.snapshot"; payload: GameSession }
  | { type: "table.thinking"; payload: { seat: number | null } }

export function useTableSocket(
  gameId: string | null,
  onSnapshot: (game: GameSession) => void,
  onThinking: (seat: number | null) => void,
) {
  useEffect(() => {
    if (!gameId) {
      onThinking(null)
      return
    }

    const socket = new WebSocket(tableWebSocketUrl(gameId))

    socket.addEventListener("message", (event) => {
      const message = parseTableSocketMessage(event.data)
      if (!message) {
        return
      }

      if (message.type === "table.snapshot") {
        onThinking(null)
        onSnapshot(message.payload)
        return
      }

      onThinking(message.payload.seat)
    })

    socket.addEventListener("close", () => {
      onThinking(null)
    })

    return () => {
      socket.close()
      onThinking(null)
    }
  }, [gameId, onSnapshot, onThinking])
}

function parseTableSocketMessage(data: unknown): TableSocketMessage | null {
  if (typeof data !== "string") {
    return null
  }

  try {
    const parsed = JSON.parse(data) as Partial<TableSocketMessage>
    if (parsed.type === "table.snapshot" || parsed.type === "table.thinking") {
      return parsed as TableSocketMessage
    }
  } catch {
    return null
  }

  return null
}
