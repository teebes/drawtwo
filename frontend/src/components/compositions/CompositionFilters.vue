<template>
  <div class="grid grid-cols-2 gap-4 sm:grid-cols-3">
    <label>
      <span class="ui-label">Game type</span>
      <select class="ui-select mt-2" :value="gameType" @change="change('game_type', $event)">
        <option value="ranked">Ranked</option>
        <option value="friendly">Friendly</option>
      </select>
    </label>
    <label>
      <span class="ui-label">Time period</span>
      <select class="ui-select mt-2" :value="days" @change="change('days', $event)">
        <option value="all">All time</option>
        <option value="7">Last 7 days</option>
        <option value="30">Last 30 days</option>
        <option value="90">Last 90 days</option>
      </select>
    </label>
    <label class="col-span-2 sm:col-span-1">
      <span class="ui-label">Ladder</span>
      <select class="ui-select mt-2" :value="gameType === 'friendly' ? 'all' : ladder" :disabled="gameType === 'friendly'" @change="change('ladder', $event)">
        <option value="all">All ladders</option>
        <option value="rapid">Rapid</option>
        <option value="daily">Daily</option>
      </select>
    </label>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
const route = useRoute()
const router = useRouter()
const gameType = computed(() => route.query.game_type === 'friendly' ? 'friendly' : 'ranked')
const days = computed(() => String(route.query.days || 'all'))
const ladder = computed(() => String(route.query.ladder || 'all'))
const change = (key: string, event: Event) => {
  const query = { ...route.query, [key]: (event.target as HTMLSelectElement).value }
  delete query.page
  delete query.matchup_page
  if (query.game_type === 'friendly') delete query.ladder
  router.push({ query })
}
</script>
