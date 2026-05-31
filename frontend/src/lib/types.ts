export type Difficulty = "beginner" | "medium" | "advanced"

export type Seat = {
  seat: number
  name: string
  role: "human" | "bot"
  stack: number
  position: string
}

export type TableState = {
  variant: "no_limit_holdem"
  stakes: {
    small_blind: number
    big_blind: number
  }
  street: string
  button_seat: number
  pot: number
  to_act: number | null
  community_cards: string[]
  seats: Seat[]
  last_action: string | null
  difficulty: Difficulty
}

export type GameSession = {
  id: string
  difficulty: Difficulty
  status: "waiting" | "active" | "complete"
  table_state: TableState
  created_at: string
  updated_at: string
}

