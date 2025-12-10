<template>
  <!-- group transform transition-all duration-300 hover:-translate-y-2 hover:shadow-xl -->
  <div class="group">
    <div :class="[
      'w-full mx-auto overflow-hidden rounded-xl border-8 border-gray-600 relative',
      containerClass,

    ]">
      <!-- Full Card Art Background -->
      <img
        :src="cardArtUrl"
        :alt="`${card.name} artwork`"
        class="absolute inset-0 w-full h-full object-cover"
        @error="onImageError"
      />

      <!-- Top panel: Name and Cost -->
  <!-- absolute top-0 left-0 right-0 bg-black/50 backdrop-blur-sm p-3 flex items-center justify-between gap-2 -->
      <div class="absolute top-0 left-0 right-0 bg-black/50 backdrop-blur-sm px-2 py-1 flex items-center justify-between gap-2">
        <!-- Name -->
        <h4 class="font-display text-base font-bold text-white truncate">
          {{ card.name }}
        </h4>

        <!-- Cost (always blue) -->
        <div class="flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold text-white bg-blue-500 shrink-0">
          {{ card.cost }}
        </div>
      </div>

      <!-- Bottom panel: Description and Stats -->
      <div class="absolute bottom-0 left-0 right-0 bg-black/50 backdrop-blur-sm px-2 py-1 flex flex-col gap-2">
        <!-- Description -->
        <p v-if="card.description" class="text-xs text-gray-200 line-clamp-2">
          {{ card.description }}
        </p>

        <!-- Stats row: Attack/Health for creatures, lightning for spells -->
        <div class="flex items-center gap-2 text-sm h-5">
          <template v-if="card.card_type === 'creature'">
            <div class="flex items-center gap-1">
              <span class="text-red-300 font-bold">⚔️</span>
              <span class="text-white font-bold">{{ card.attack }}</span>
            </div>
            <div class="flex items-center gap-1">
              <span class="text-green-300 font-bold">❤️</span>
              <span class="text-white font-bold">{{ card.health }}</span>
            </div>
          </template>
          <template v-else>
            <span class="text-yellow-300 text-lg">🔮</span>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Card } from '../../types/card'

interface Props {
  card: Card
  heightMode?: 'fixed' | 'min' | 'auto' | 'aspect-ratio'
  height?: 'sm' | 'md' | 'lg' | 'xl'
}

const props = withDefaults(defineProps<Props>(), {
  heightMode: 'aspect-ratio',
  height: 'lg'
})

const imageError = ref(false)

const cardArtUrl = computed(() => {

  // If image failed to load, use placeholder
  if (imageError.value) {
    return '/card_backs/placeholder.svg'
  }

  // If card has a custom art URL from backend (user-uploaded), use it
  if (props.card.art_url) {
    return props.card.art_url
  }

  // Default fallback for other titles without custom art
  return '/card_backs/placeholder.svg'
})

const onImageError = () => {
  imageError.value = true
}

const containerClass = computed(() => {
  // If using aspect ratio mode, use aspect-[5/7] (card ratio: 5 width : 7 height)
  if (props.heightMode === 'aspect-ratio') {
    return 'aspect-[5/7]'
  }

  // Otherwise use the old height-based approach
  const heightSizes = {
    sm: 'h-72',     // 18rem (288px)
    md: 'h-80',     // 20rem (320px)
    lg: 'h-96',     // 24rem (384px)
    xl: 'h-[28rem]' // 28rem (448px)
  }

  const minHeightSizes = {
    sm: 'min-h-72',     // min 18rem (288px)
    md: 'min-h-80',     // min 20rem (320px)
    lg: 'min-h-96',     // min 24rem (384px)
    xl: 'min-h-[28rem]' // min 28rem (448px)
  }

  switch (props.heightMode) {
    case 'fixed':
      return heightSizes[props.height]
    case 'min':
      return minHeightSizes[props.height]
    case 'auto':
      return '' // No height constraint
    default:
      return heightSizes[props.height]
  }
})

const borderClass = computed(() => {
  const borderMap = {
    spell: 'border-blue-500',
    creature: 'border-yellow-500'
  }
  return borderMap[props.card.card_type]
})
</script>