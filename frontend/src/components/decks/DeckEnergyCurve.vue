<template>
  <div v-if="powerCurve.length" class="mt-4 border-t border-gray-200 pt-4 dark:border-gray-700">
    <div class="mb-2 text-center">
      <h2 class="text-xs font-semibold uppercase tracking-wide text-gray-600 dark:text-gray-300">Cards by energy cost</h2>
    </div>
    <div class="overflow-x-auto pb-1">
      <div class="mx-auto flex w-max items-end gap-1" role="img" :aria-label="curveDescription">
        <div v-for="bucket in powerCurve" :key="bucket.cost" class="flex min-w-[28px] flex-col items-center" aria-hidden="true">
          <span class="mb-1 text-[10px] font-semibold text-gray-500 dark:text-gray-400">{{ bucket.count }}</span>
          <div
            class="w-5 rounded-t bg-secondary-500 transition-all duration-300"
            :class="bucket.count === 0 ? 'opacity-20' : 'opacity-90'"
            :style="{ height: `${bucket.height}px` }"
          />
          <span class="mt-1 text-[10px] font-semibold text-gray-600 dark:text-gray-300">{{ bucket.cost }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ cards: Array<{ cost?: number; count: number }> }>()

const powerCurve = computed(() => {
  const costCounts = new Map<number, number>()
  for (const card of props.cards) {
    if (card.cost === undefined || !Number.isFinite(card.cost) || card.count <= 0) continue
    const cost = Math.max(0, Math.round(card.cost))
    costCounts.set(cost, (costCounts.get(cost) || 0) + card.count)
  }
  if (!costCounts.size) return []

  const minCost = costCounts.has(0) ? 0 : 1
  const maxCost = Math.max(...costCounts.keys())
  const maxCount = Math.max(...costCounts.values())
  return Array.from({ length: maxCost - minCost + 1 }, (_, index) => {
    const cost = index + minCost
    const count = costCounts.get(cost) || 0
    const height = count > 0 ? Math.max(8, Math.round((count / maxCount) * 36) + 4) : 8
    return { cost, count, height }
  })
})

const curveDescription = computed(() => 'Cards by energy cost: ' + powerCurve.value
  .map(bucket => `${bucket.cost} energy: ${bucket.count} ${bucket.count === 1 ? 'card' : 'cards'}`)
  .join('; '))
</script>
