import axios from '@/config/api'

export interface QueueRequest {
  title_slug: string
  deck_id: number
}

export interface QueueResponse {
  id: number
  status: string
  title: {
    slug: string
    name: string
  }
  deck: {
    id: number
    name: string
    hero: string
  }
  elo_rating: number
  message: string
}

export const matchmakingApi = {
  // Queue for a ranked match
  async queueForRankedMatch(data: QueueRequest): Promise<QueueResponse> {
    const response = await axios.post('/gameplay/matchmaking/queue/', data)
    return response.data
  }
}
