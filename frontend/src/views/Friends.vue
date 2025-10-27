<template>
  <div class="min-h-screen flex flex-col items-center p-8">
    <div class="w-full max-w-2xl">
      <h1 class="text-3xl font-bold mb-8">Friends</h1>

      <!-- Add Friend Section -->
      <div class="mb-8 p-6 bg-gray-800 rounded-lg border border-gray-700">
        <h2 class="text-xl font-semibold mb-4">Add Friend</h2>
        <form @submit.prevent="sendFriendRequest" class="flex gap-2">
          <input
            v-model="newFriendUsername"
            type="text"
            placeholder="Enter username"
            class="flex-1 px-4 py-2 bg-gray-900 border border-gray-700 rounded focus:outline-none focus:border-blue-500"
            required
          />
          <button
            type="submit"
            :disabled="loading"
            class="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded font-semibold transition-colors"
          >
            {{ loading ? 'Sending...' : 'Send Request' }}
          </button>
        </form>
        <div v-if="error" class="mt-2 text-red-400 text-sm">{{ error }}</div>
        <div v-if="success" class="mt-2 text-green-400 text-sm">{{ success }}</div>
      </div>

      <!-- Friends List -->
      <div class="mb-8">
        <h2 class="text-xl font-semibold mb-4">Friends ({{ acceptedFriends.length }})</h2>
        <div v-if="acceptedFriends.length === 0" class="text-gray-400 text-center py-8">
          No friends yet. Send a friend request to get started!
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="friendship in acceptedFriends"
            :key="friendship.id"
            class="p-4 bg-gray-800 rounded-lg border border-gray-700 flex justify-between items-center"
          >
            <div class="flex items-center gap-4">
              <div
                v-if="friendship.friend_data.avatar"
                class="w-10 h-10 rounded-full bg-gray-700 overflow-hidden"
              >
                <img :src="friendship.friend_data.avatar" alt="Avatar" class="w-full h-full object-cover" />
              </div>
              <div v-else class="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center">
                <span class="text-lg font-bold">{{ friendship.friend_data.display_name[0].toUpperCase() }}</span>
              </div>
              <div>
                <div class="font-semibold">{{ friendship.friend_data.display_name }}</div>
                <div class="text-sm text-gray-400">{{ friendship.friend_data.username || friendship.friend_data.email }}</div>
              </div>
            </div>
            <button
              @click="removeFriend(friendship.id)"
              class="px-4 py-2 bg-red-600 hover:bg-red-700 rounded text-sm font-semibold transition-colors"
            >
              Remove
            </button>
          </div>
        </div>
      </div>

      <!-- Pending Requests (Received) -->
      <div class="mb-8">
        <h2 class="text-xl font-semibold mb-4">Pending Requests ({{ pendingReceived.length }})</h2>
        <div v-if="pendingReceived.length === 0" class="text-gray-400 text-center py-8">
          No pending friend requests
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="friendship in pendingReceived"
            :key="friendship.id"
            class="p-4 bg-gray-800 rounded-lg border border-yellow-700 flex justify-between items-center"
          >
            <div class="flex items-center gap-4">
              <div
                v-if="friendship.friend_data.avatar"
                class="w-10 h-10 rounded-full bg-gray-700 overflow-hidden"
              >
                <img :src="friendship.friend_data.avatar" alt="Avatar" class="w-full h-full object-cover" />
              </div>
              <div v-else class="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center">
                <span class="text-lg font-bold">{{ friendship.friend_data.display_name[0].toUpperCase() }}</span>
              </div>
              <div>
                <div class="font-semibold">{{ friendship.friend_data.display_name }}</div>
                <div class="text-sm text-gray-400">{{ friendship.friend_data.username || friendship.friend_data.email }}</div>
              </div>
            </div>
            <div class="flex gap-2">
              <button
                @click="acceptRequest(friendship.id)"
                class="px-4 py-2 bg-green-600 hover:bg-green-700 rounded text-sm font-semibold transition-colors"
              >
                Accept
              </button>
              <button
                @click="declineRequest(friendship.id)"
                class="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded text-sm font-semibold transition-colors"
              >
                Decline
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Pending Requests (Sent) -->
      <div class="mb-8">
        <h2 class="text-xl font-semibold mb-4">Sent Requests ({{ pendingSent.length }})</h2>
        <div v-if="pendingSent.length === 0" class="text-gray-400 text-center py-8">
          No pending sent requests
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="friendship in pendingSent"
            :key="friendship.id"
            class="p-4 bg-gray-800 rounded-lg border border-gray-700 flex justify-between items-center opacity-75"
          >
            <div class="flex items-center gap-4">
              <div
                v-if="friendship.friend_data.avatar"
                class="w-10 h-10 rounded-full bg-gray-700 overflow-hidden"
              >
                <img :src="friendship.friend_data.avatar" alt="Avatar" class="w-full h-full object-cover" />
              </div>
              <div v-else class="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center">
                <span class="text-lg font-bold">{{ friendship.friend_data.display_name[0].toUpperCase() }}</span>
              </div>
              <div>
                <div class="font-semibold">{{ friendship.friend_data.display_name }}</div>
                <div class="text-sm text-gray-400">{{ friendship.friend_data.username || friendship.friend_data.email }}</div>
                <div class="text-xs text-yellow-400 mt-1">Waiting for response...</div>
              </div>
            </div>
            <button
              @click="removeFriend(friendship.id)"
              class="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded text-sm font-semibold transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { friendsApi } from '@/services/friends'
import type { Friendship } from '@/types/auth'

const friendships = ref<Friendship[]>([])
const newFriendUsername = ref('')
const loading = ref(false)
const error = ref('')
const success = ref('')

// Computed lists
const acceptedFriends = computed(() =>
  friendships.value.filter(f => f.status === 'accepted')
)

const pendingReceived = computed(() =>
  friendships.value.filter(f => f.status === 'pending' && !f.is_initiator)
)

const pendingSent = computed(() =>
  friendships.value.filter(f => f.status === 'pending' && f.is_initiator)
)

// Load friendships
const loadFriendships = async () => {
  try {
    friendships.value = await friendsApi.getFriendships()
  } catch (err: any) {
    console.error('Failed to load friendships:', err)
  }
}

// Send friend request
const sendFriendRequest = async () => {
  if (!newFriendUsername.value.trim()) return

  loading.value = true
  error.value = ''
  success.value = ''

  try {
    await friendsApi.sendFriendRequest({ username: newFriendUsername.value })
    success.value = `Friend request sent to ${newFriendUsername.value}!`
    newFriendUsername.value = ''
    await loadFriendships()
  } catch (err: any) {
    if (err.response?.data) {
      const errors = err.response.data
      if (errors.username) {
        error.value = Array.isArray(errors.username) ? errors.username[0] : errors.username
      } else if (errors.error) {
        error.value = errors.error
      } else {
        error.value = 'Failed to send friend request'
      }
    } else {
      error.value = 'Failed to send friend request'
    }
  } finally {
    loading.value = false
  }
}

// Accept friend request
const acceptRequest = async (friendshipId: number) => {
  try {
    await friendsApi.acceptFriendRequest(friendshipId)
    await loadFriendships()
  } catch (err) {
    console.error('Failed to accept friend request:', err)
  }
}

// Decline friend request
const declineRequest = async (friendshipId: number) => {
  try {
    await friendsApi.declineFriendRequest(friendshipId)
    await loadFriendships()
  } catch (err) {
    console.error('Failed to decline friend request:', err)
  }
}

// Remove friend
const removeFriend = async (friendshipId: number) => {
  if (!confirm('Are you sure you want to remove this friend?')) return

  try {
    await friendsApi.removeFriend(friendshipId)
    await loadFriendships()
  } catch (err) {
    console.error('Failed to remove friend:', err)
  }
}

onMounted(() => {
  loadFriendships()
})
</script>
