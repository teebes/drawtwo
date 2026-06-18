import rawAxios from 'axios'
import api from '@/config/api'

export const INTRO_SCENARIO_SLUG = 'intro-archetype-v1'

interface IntroScenarioResponse {
  id: number
  title_slug: string
  viewer_side: 'side_a' | 'side_b'
  access_token: string
  game_type: 'intro'
}

const tokenStorageKey = (gameId: string | number): string => {
  return `intro-game-access-token:${gameId}`
}

const introAxios = rawAxios.create({
  baseURL: api.defaults.baseURL,
})

export const saveIntroGameAccessToken = (
  gameId: string | number,
  token: string
): void => {
  sessionStorage.setItem(tokenStorageKey(gameId), token)
}

export const getIntroGameAccessToken = (
  gameId: string | number
): string | null => {
  return sessionStorage.getItem(tokenStorageKey(gameId))
}

export const fetchIntroGame = (gameId: string | number) => {
  const token = getIntroGameAccessToken(gameId)
  if (!token) {
    return null
  }

  return introAxios.get(`/gameplay/games/${gameId}/`, {
    params: {
      guest_token: token,
    },
  })
}

export const startIntroScenario = async (): Promise<IntroScenarioResponse> => {
  const response = await introAxios.post(
    `/gameplay/scenarios/${INTRO_SCENARIO_SLUG}/start/`
  )
  const data = response.data as IntroScenarioResponse
  saveIntroGameAccessToken(data.id, data.access_token)
  return data
}
