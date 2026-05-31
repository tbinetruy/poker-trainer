export type Difficulty = "beginner" | "medium" | "advanced"

export type Seat = {
  seat: number
  name: string
  role: "human" | "bot"
  stack: number
  position: string
  hole_cards: string[]
  status: "active" | "folded" | "all_in"
  committed: number
  street_bet: number
}

export type LegalAction =
  | { action: "fold" }
  | { action: "check" }
  | { action: "call"; amount: number }
  | { action: "bet"; min_amount: number; max_amount: number }
  | { action: "raise"; min_amount: number; max_amount: number }

export type TableState = {
  variant: "no_limit_holdem"
  status: "active" | "complete"
  hand_id: string
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
  legal_actions: LegalAction[]
  hand_history: Array<Record<string, unknown>>
  winners: Array<{ seat: number; amount: number }>
}

export type GameSession = {
  id: string
  difficulty: Difficulty
  status: "active" | "complete"
  table_state: TableState
  created_at: string
  updated_at: string
}
