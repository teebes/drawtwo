<template>
  <form v-if="editing" class="mt-4 max-w-lg space-y-3" @submit.prevent="saveName" @keydown.esc.prevent="cancelEditing">
    <label for="composition-name" class="ui-label">Composition name</label>
    <input
      id="composition-name"
      ref="nameInput"
      v-model="draft"
      type="text"
      maxlength="120"
      class="ui-input"
      :disabled="saving"
      aria-describedby="composition-name-help"
    />
    <p id="composition-name-help" class="text-xs text-gray-500 dark:text-gray-400">
      Shown to everyone. Leave blank to use the card names.
      Title editors and ranked win leaders can change it. Daily wins come first;
      rapid wins break ties. All-time wins count.
    </p>
    <p v-if="error" class="ui-alert ui-alert-error" role="alert">{{ error }}</p>
    <div class="flex gap-2">
      <button type="submit" class="ui-btn ui-btn-sm ui-btn-primary" :disabled="saving || normalizedDraft === (name || '')">
        {{ saving ? 'Saving…' : 'Save name' }}
      </button>
      <button type="button" class="ui-btn ui-btn-sm ui-btn-outline" :disabled="saving" @click="cancelEditing">Cancel</button>
    </div>
  </form>
  <button v-else type="button" class="mt-3 inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-primary-700 dark:text-gray-400 dark:hover:text-primary-300" @click="startEditing">
    <Pencil class="h-3.5 w-3.5" aria-hidden="true" />
    {{ name ? 'Rename composition' : 'Name composition' }}
  </button>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { Pencil } from 'lucide-vue-next'
import axios from '../../config/api'

const props = defineProps<{ titleSlug: string; code: string; name?: string }>()
const emit = defineEmits<{ saved: [name: string] }>()
const editing = ref(false)
const saving = ref(false)
const draft = ref('')
const error = ref('')
const nameInput = ref<HTMLInputElement | null>(null)
const normalizedDraft = computed(() => draft.value.trim().replace(/\s+/g, ' '))
let controller: AbortController | null = null

const startEditing = async () => {
  draft.value = props.name || ''
  error.value = ''
  editing.value = true
  await nextTick()
  nameInput.value?.focus()
  nameInput.value?.select()
}

const cancelEditing = () => {
  if (!saving.value) editing.value = false
}

const saveName = async () => {
  if (saving.value) return
  saving.value = true
  error.value = ''
  controller = new AbortController()
  try {
    const response = await axios.put<{ name: string }>(
      `/collection/titles/${encodeURIComponent(props.titleSlug)}/compositions/${encodeURIComponent(props.code)}/name/`,
      { name: normalizedDraft.value },
      { signal: controller.signal }
    )
    emit('saved', response.data.name)
    editing.value = false
  } catch (err: any) {
    if (err.code !== 'ERR_CANCELED') {
      error.value = err.response?.data?.error || 'Unable to save the composition name. Try again.'
    }
  } finally {
    saving.value = false
  }
}

onBeforeUnmount(() => controller?.abort())
</script>
