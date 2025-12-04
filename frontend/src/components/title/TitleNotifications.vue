<template>
  <div v-if="notifications.length > 0" class="space-y-3">
    <div
      v-for="notification in notifications"
      @click="handleNotificationClick(notification)"
      :key="`${notification.type}-${notification.ref_id}`"
      :class="[
        'rounded-lg p-4 transition-all border cursor-pointer',
        ranked_notification_types.includes(notification.type)
          ? ranked_notifications
          : 'dark:text-white dark:border-secondary-800 dark:bg-secondary-950 border-secondary-300 bg-secondary-200 text-black'
      ]">
      <!-- Challenge Notification -->
      <div v-if="notification.type === 'game_challenge'" class="flex items-center justify-between">
        <div class="flex items-center">
          {{ notification.message }}
        </div>
        <div class="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-2">
          <button
            @click="openAcceptModal(notification)"
            :disabled="actionLoading[notification.ref_id]"
            class="inline-flex h-10 items-center justify-center rounded-lg bg-secondary-600 px-4 text-sm font-medium text-white hover:bg-secondary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Accept
          </button>
          <button
            @click="handleDecline(notification.ref_id)"
            :disabled="actionLoading[notification.ref_id]"
            class="inline-flex h-10 px-4 text-sm items-center justify-center rounded-lg border border-secondary-600 font-medium text-secondary-600 hover:bg-secondary-300 transition-colors dark:border-secondary-600 dark:text-secondary-400 dark:hover:bg-secondary-900 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ actionLoading[notification.ref_id] ? 'Declining...' : 'Decline' }}
          </button>
        </div>
      </div>

      <!-- Other Notifications (game_started, game_ended) -->
      <div v-else class="flex h-10 items-center">
        <div v-if="ranked_notification_types.includes(notification.type)" class="mr-2">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary-100 text-2xl font-bold text-secondary-600">⚔️</div>
        </div>
        <div v-if="friendly_notification_types.includes(notification.type)" class="mr-2">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary-100 text-2xl font-bold text-secondary-600">🤝</div>
        </div>
        <div v-if="notification.type == 'friend_request'" class="mr-2">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary-100 text-2xl font-bold text-secondary-600">👥</div>
        </div>
        <div class="ml-2">{{ notification.message }}</div>
      </div>
    </div>

    <!-- Deck Selection Modal -->
    <DeckSelectModal
      :show="showDeckModal"
      :decks="decks"
      :loading="decksLoading"
      :confirming="acceptingChallenge"
      title="Accept Challenge"
      subtitle="Choose a deck to play with"
      confirm-text="Accept Challenge"
      @close="closeDeckModal"
      @confirm="handleAcceptWithDeck"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '../../stores/notifications'
import { challengesApi } from '../../services/challenges'
import DeckSelectModal from '../modals/DeckSelectModal.vue'
import type { Notification } from '../../types/notification'

interface DeckData {
  id: number
  name: string
  hero: {
    id: number
    name: string
    slug: string
    art_url?: string | null
  }
  card_count: number
}

const props = defineProps<{
  notifications: Notification[]
  decks: DeckData[]
  decksLoading?: boolean
  titleSlug: string
}>()

const emit = defineEmits<{
  (e: 'challenge-accepted', challengeId: number): void
  (e: 'challenge-declined', challengeId: number): void
}>()

const router = useRouter()
const notificationStore = useNotificationStore()

const ranked_notification_types = ['game_ranked_queued', 'game_ranked']
const friendly_notification_types = ['game_friendly', 'game_challenge']
const ranked_notifications = 'bg-primary-100 border-primary-500 dark:bg-primary-950 dark:border-primary-800 text-black dark:text-white'

const showDeckModal = ref(false)
const selectedChallengeId = ref<number | null>(null)
const acceptingChallenge = ref(false)
const actionLoading = ref<Record<number, boolean>>({})

const openAcceptModal = (notification: Notification) => {
  selectedChallengeId.value = notification.ref_id
  showDeckModal.value = true
}

const closeDeckModal = () => {
  showDeckModal.value = false
  selectedChallengeId.value = null
}

const handleAcceptWithDeck = async (deck: DeckData) => {
  if (!selectedChallengeId.value) return

  try {
    acceptingChallenge.value = true
    const { game_id } = await challengesApi.acceptChallenge(selectedChallengeId.value, deck.id)
    notificationStore.success('Challenge accepted! Starting game...')
    emit('challenge-accepted', selectedChallengeId.value)
    closeDeckModal()
    router.push({ name: 'Board', params: { game_id, slug: props.titleSlug } })
  } catch (err) {
    console.error('Error accepting challenge:', err)
    notificationStore.handleApiError(err as Error)
  } finally {
    acceptingChallenge.value = false
  }
}

const handleDecline = async (challengeId: number) => {
  try {
    actionLoading.value[challengeId] = true
    await challengesApi.declineChallenge(challengeId)
    notificationStore.success('Challenge declined')
    emit('challenge-declined', challengeId)
  } catch (err) {
    console.error('Error declining challenge:', err)
    notificationStore.handleApiError(err as Error)
  } finally {
    actionLoading.value[challengeId] = false
  }
}

const handleNotificationClick = (notification: Notification) => {
  if (notification.type === 'game_ranked') {
    router.push({
      name: 'Board',
      params: { game_id: notification.ref_id, slug: props.titleSlug }
    })
  } else if (notification.type === 'game_friendly') {
    router.push({
      name: 'Board',
      params: { game_id: notification.ref_id, slug: props.titleSlug }
    })
  } else if (notification.type === 'friend_request') {
    router.push({
      name: 'Friends',
    })
  }
}
</script>
