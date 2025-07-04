<template>
  <div
    @click="handleClick"
    :class="[
      'w-16 h-20 border-2 border-dashed border-green-400 bg-green-100/20 rounded-lg',
      'flex items-center justify-center cursor-pointer transition-all duration-200',
      'hover:bg-green-100/40 hover:border-green-300'
    ]"
  >
    <div class="text-green-400 text-2xl">+</div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  position: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'placement-clicked': [position: number]
}>()

const handleClick = () => {
  emit('placement-clicked', props.position)
}
</script>