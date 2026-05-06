import { defineStore } from 'pinia'
import axios from '../config/api'

// Types for title data
interface Title {
  id: number
  name: string
  slug: string
  description?: string
  created_at?: string
  updated_at?: string
  art_url?: string
  [key: string]: any // Allow for additional title fields
}

interface TitleState {
  currentTitle: Title | null
  editableTitleContext: Title | null
  loading: boolean
  error: string | null
  errorStatus: number | null
}

export const useTitleStore = defineStore('title', {
  state: (): TitleState => ({
    currentTitle: null,
    editableTitleContext: null,
    loading: false,
    error: null,
    errorStatus: null
  }),

  getters: {
    isViewingTitle: (state): boolean => state.currentTitle !== null,
    titleName: (state): string | null => state.currentTitle?.name || null,
    titleSlug: (state): string | null => state.currentTitle?.slug || null,
    editableTitleSlug: (state): string | null => state.editableTitleContext?.slug || null
  },

  actions: {
    async loadTitle(slug: string): Promise<Title> {
      // Don't reload if we already have the same title
      if (this.currentTitle?.slug === slug) {
        return this.currentTitle
      }

      this.loading = true
      this.error = null
      this.errorStatus = null

      try {
        // const response = await axios.get(`/builder/titles/${slug}/`)
        const response = await axios.get(`/titles/${slug}/`)
        this.currentTitle = response.data as Title
        if (this.currentTitle.can_edit === true) {
          this.editableTitleContext = this.currentTitle
        }
        return this.currentTitle
      } catch (error: any) {
        this.error = error.response?.data?.detail || error.response?.data?.message || error.message || 'Failed to load title'
        this.errorStatus = error.response?.status || null
        this.currentTitle = null
        throw error
      } finally {
        this.loading = false
      }
    },

    setCurrentTitle(titleData: Title): void {
      this.currentTitle = titleData
      this.error = null
      if (titleData.can_edit === true) {
        this.editableTitleContext = titleData
      }
    },

    clearCurrentTitle(): void {
      this.currentTitle = null
      this.error = null
      this.errorStatus = null
      this.loading = false
    },

    clearEditableTitleContext(): void {
      this.editableTitleContext = null
    }
  }
})
