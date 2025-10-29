export interface User {
  id: number
  email: string
  username: string | null
  display_name: string
  avatar: string | null
  is_email_verified: boolean
  is_staff: boolean
  status: string
  created_at: string
  updated_at: string
}

export interface FriendUser {
  id: number
  email: string
  username: string | null
  display_name: string
  avatar: string | null
}

export interface Friendship {
  id: number
  friend: number
  friend_data: FriendUser
  status: 'pending' | 'accepted' | 'declined' | 'blocked'
  is_initiator: boolean
  created_at: string
  updated_at: string
}

export interface FriendRequest {
  username: string
}
