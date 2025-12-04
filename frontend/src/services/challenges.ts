import axios from '@/config/api'
import type { FriendlyChallenge, PendingChallengesResponse } from '@/types/challenge'

export const challengesApi = {
  async createChallenge(params: {
    title_slug: string
    challengee_user_id: number
    challenger_deck_id: number
  }): Promise<FriendlyChallenge> {
    const response = await axios.post('/gameplay/challenges/', params)
    return response.data
  },

  async listPending(titleSlug: string): Promise<PendingChallengesResponse> {
    const response = await axios.get(`/gameplay/challenges/pending/${titleSlug}/`)
    return response.data
  },

  async acceptChallenge(challengeId: number, challengeeDeckId: number): Promise<{ game_id: number }> {
    const response = await axios.post(`/gameplay/challenges/${challengeId}/accept/`, {
      challengee_deck_id: challengeeDeckId
    })
    return response.data
  },

  async declineChallenge(challengeId: number): Promise<{ success: boolean; message: string }> {
    const response = await axios.post(`/gameplay/challenges/${challengeId}/decline/`)
    return response.data
  }
}
