export type FriendlyChallengeStatus = 'pending' | 'accepted' | 'cancelled' | 'expired'

export interface FriendlyChallenge {
  id: number
  status: FriendlyChallengeStatus
  title: {
    id: number
    name: string
    slug: string
  }
  challenger: {
    id: number
    display_name: string
  }
  challengee: {
    id: number
    display_name: string
  }
  challenger_deck: {
    id: number
    name: string
    hero: string
  }
}

export interface PendingChallengesResponse {
  incoming: FriendlyChallenge[]
  outgoing: FriendlyChallenge[]
}
