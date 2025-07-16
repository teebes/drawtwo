import { defineStore } from 'pinia'
import axios from '../config/api.js'

export const useTitleStore = defineStore('title', {
  state: () => ({
    currentTitle: null,
    loading: false,
    error: null
  }),

  getters: {
    isViewingTitle: (state) => state.currentTitle !== null,
    titleName: (state) => state.currentTitle?.name || null,
    titleSlug: (state) => state.currentTitle?.slug || null
  },

  actions: {
    async loadTitle(slug) {
      // Don't reload if we already have the same title
      if (this.currentTitle?.slug === slug) {
        return this.currentTitle
      }

      this.loading = true
      this.error = null

      try {
        const response = await axios.get(`/builder/titles/${slug}/`)
        this.currentTitle = response.data
        return this.currentTitle
      } catch (error) {
        this.error = error.response?.data?.message || error.message || 'Failed to load title'
        this.currentTitle = null
        throw error
      } finally {
        this.loading = false
      }
    },

    setCurrentTitle(titleData) {
      this.currentTitle = titleData
      this.error = null
    },

    clearCurrentTitle() {
      this.currentTitle = null
      this.error = null
      this.loading = false
    }
  }
})