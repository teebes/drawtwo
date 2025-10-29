import axios from '@/config/api'
import type { Friendship, FriendRequest } from '@/types/auth'

export const friendsApi = {
  // Get all friendships (both friends and pending requests)
  async getFriendships(): Promise<Friendship[]> {
    const response = await axios.get('/auth/friends/')
    return response.data
  },

  // Send a friend request
  async sendFriendRequest(data: FriendRequest): Promise<Friendship> {
    const response = await axios.post('/auth/friends/', data)
    return response.data
  },

  // Accept a friend request
  async acceptFriendRequest(friendshipId: number): Promise<Friendship> {
    const response = await axios.patch(`/auth/friends/${friendshipId}/`, {
      action: 'accept'
    })
    return response.data
  },

  // Decline a friend request
  async declineFriendRequest(friendshipId: number): Promise<void> {
    await axios.patch(`/auth/friends/${friendshipId}/`, {
      action: 'decline'
    })
  },

  // Remove a friend
  async removeFriend(friendshipId: number): Promise<void> {
    await axios.delete(`/auth/friends/${friendshipId}/`)
  }
}
