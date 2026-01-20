export type NotificationType =
  | 'game_friendly'
  | 'game_challenge'
  | 'game_started'
  | 'game_ended'
  | 'game_ranked'
  | 'game_ranked_queued'
  | 'friend_request'
  | 'game_pve'

export interface Notification {
  ref_id: number
  type: NotificationType
  message: string
  is_user_turn?: boolean
}
