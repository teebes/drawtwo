<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="show"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
        role="dialog"
        aria-modal="true"
      >
        <!-- Backdrop -->
        <div
          class="fixed inset-0 bg-gray-900/75 transition-opacity"
          @click="close"
        ></div>

        <!-- Modal Panel -->
        <div
          class="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:w-full sm:max-w-2xl dark:bg-gray-900 max-h-[90vh] flex flex-col"
        >
            <button
                @click="close"
                class="absolute top-0 right-0 z-10 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 bg-white/50 dark:bg-black/50 rounded-full p-1"
            >
                <span class="sr-only">Close</span>
                <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
            <div class="flex-1 overflow-y-auto">
                <slot></slot>
            </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * BaseModal - A reusable modal component with backdrop and close functionality.
 *
 * Usage:
 *
 * 1. Import the component:
 *    import BaseModal from '@/components/modals/BaseModal.vue'
 *
 * 2. Create reactive state for modal visibility:
 *    const modalOpen = ref(false)
 *
 * 3. Create open/close handlers:
 *    const openModal = () => { modalOpen.value = true }
 *    const closeModal = () => { modalOpen.value = false }
 *
 * 4. Use in template:
 *    <button @click="openModal">Open Modal</button>
 *    <BaseModal :show="modalOpen" @close="closeModal">
 *      <div class="p-6">
 *        <h2>Modal Title</h2>
 *        <p>Modal content goes here</p>
 *      </div>
 *    </BaseModal>
 *
 * Props:
 * - show (boolean, required): Controls the visibility of the modal
 *
 * Events:
 * - close: Emitted when the modal should be closed (clicking backdrop or close button)
 *
 * Slots:
 * - default: The content to display inside the modal panel
 *
 * Features:
 * - Automatically teleports to body
 * - Includes backdrop that closes modal on click
 * - Close button in top-right corner
 * - Fade transition animations
 * - Responsive design with max-width and scrollable content
 * - Dark mode support
 */
defineProps<{
  show: boolean
}>()

const emit = defineEmits(['close'])

const close = () => {
  emit('close')
}
</script>

<style scoped>
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>
