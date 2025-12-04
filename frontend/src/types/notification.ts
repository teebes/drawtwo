export type NotificationType =
  | 'game_friendly'
  | 'game_challenge'
  | 'game_started'
  | 'game_ended'
  | 'game_ranked'
  | 'game_ranked_queued'
  | 'friend_request'

export interface Notification {
  ref_id: number
  type: NotificationType
  message: string
}
