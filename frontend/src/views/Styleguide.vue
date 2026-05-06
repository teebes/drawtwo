<template>
  <div class="ui-page">
    <main class="ui-page-container">
      <header class="ui-page-header">
        <h1 class="ui-page-title">Styleguide</h1>
        <p class="ui-page-subtitle">
          Shared UI primitives used by admin, configuration, and operational screens.
        </p>
      </header>

      <div class="space-y-10">
        <section class="space-y-4">
          <div>
            <h2 class="ui-panel-title">Page Shell</h2>
            <p class="ui-panel-subtitle">
              Use these for full-page tool screens such as Control Panel and Game Config.
            </p>
          </div>

          <div class="ui-panel">
            <div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <h3 class="ui-page-title text-2xl lg:text-3xl">Screen Title</h3>
                <p class="ui-page-meta">Context, world, or screen description</p>
              </div>
              <button class="ui-btn ui-btn-md ui-btn-primary">Primary Action</button>
            </div>
            <code class="mt-5 text-sm text-gray-500 dark:text-gray-400">
              ui-page, ui-page-container, ui-page-header, ui-page-title
            </code>
          </div>
        </section>

        <section class="space-y-4">
          <div>
            <h2 class="ui-panel-title">Panels</h2>
            <p class="ui-panel-subtitle">
              Primary panels are bordered 8px surfaces. Muted panels are for compact nested content.
            </p>
          </div>

          <div class="grid gap-6 lg:grid-cols-2">
            <div class="ui-panel">
              <div class="ui-panel-heading">
                <Settings class="ui-panel-icon" aria-hidden="true" />
                <h3 class="ui-panel-title">Primary Panel</h3>
              </div>
              <p class="text-sm text-gray-600 dark:text-gray-300">
                Used for settings groups, admin dashboards, tables, and form sections.
              </p>
              <code class="mt-5 text-sm text-gray-500 dark:text-gray-400">ui-panel</code>
            </div>

            <div class="ui-panel">
              <h3 class="ui-panel-title mb-4">Muted Surfaces</h3>
              <div class="grid gap-3 sm:grid-cols-2">
                <div class="ui-panel-muted">
                  <p class="text-sm text-gray-500 dark:text-gray-400">Queued Players</p>
                  <p class="ui-stat-value">12</p>
                </div>
                <div class="ui-panel-muted">
                  <p class="text-sm text-gray-500 dark:text-gray-400">Active Games</p>
                  <p class="text-3xl font-bold text-green-600 dark:text-green-400">8</p>
                </div>
              </div>
              <code class="mt-5 text-sm text-gray-500 dark:text-gray-400">ui-panel-muted</code>
            </div>
          </div>
        </section>

        <section class="space-y-4">
          <div>
            <h2 class="ui-panel-title">Navigation Tabs</h2>
            <p class="ui-panel-subtitle">
              Use these for dense tool navigation with horizontal overflow.
            </p>
          </div>

          <div class="ui-tabs-shell">
            <div class="ui-tabs-scroll">
              <nav class="ui-tabs" aria-label="Styleguide tabs">
                <button
                  v-for="tab in tabs"
                  :key="tab"
                  type="button"
                  :class="['ui-tab', activeTab === tab ? 'ui-tab-active' : 'ui-tab-inactive']"
                  @click="activeTab = tab"
                >
                  {{ tab }}
                </button>
              </nav>
            </div>
          </div>
        </section>

        <section class="space-y-4">
          <div>
            <h2 class="ui-panel-title">Forms And Buttons</h2>
            <p class="ui-panel-subtitle">
              Inputs, selects, checkboxes, and buttons share sizing and focus states.
            </p>
          </div>

          <div class="ui-panel">
            <div class="grid gap-5 md:grid-cols-3">
              <label class="block">
                <span class="ui-label">Number input</span>
                <input class="ui-input mt-2" type="number" value="30" />
              </label>
              <label class="block">
                <span class="ui-label">Select input</span>
                <select class="ui-select mt-2">
                  <option>Rapid</option>
                  <option>Daily</option>
                </select>
              </label>
              <label class="mt-8 flex items-center gap-3 md:mt-8">
                <input class="ui-checkbox" type="checkbox" checked />
                <span class="ui-label">Enabled setting</span>
              </label>
            </div>

            <div class="mt-6 flex flex-wrap gap-3">
              <button class="ui-btn ui-btn-md ui-btn-primary">Primary</button>
              <button class="ui-btn ui-btn-md ui-btn-secondary">Secondary</button>
              <button class="ui-btn ui-btn-md ui-btn-outline">Outline</button>
              <button class="ui-btn ui-btn-md ui-btn-danger">Danger</button>
            </div>
          </div>
        </section>

        <section class="space-y-4">
          <div>
            <h2 class="ui-panel-title">Alerts And Badges</h2>
            <p class="ui-panel-subtitle">
              Use alerts for inline feedback and badges for compact state labels.
            </p>
          </div>

          <div class="grid gap-6 lg:grid-cols-2">
            <div class="space-y-3">
              <div class="ui-alert ui-alert-success flex items-start gap-3">
                <CheckCircle class="mt-0.5 h-4 w-4 flex-none" aria-hidden="true" />
                <span>Configuration saved.</span>
              </div>
              <div class="ui-alert ui-alert-warning flex items-start gap-3">
                <AlertTriangle class="mt-0.5 h-4 w-4 flex-none" aria-hidden="true" />
                <span>Minimum deck size cannot exceed maximum deck size.</span>
              </div>
              <div class="ui-alert ui-alert-error">Failed to load users.</div>
            </div>

            <div class="ui-panel">
              <div class="flex flex-wrap gap-3">
                <span class="ui-status-badge ui-status-success">Enabled</span>
                <span class="ui-status-badge ui-status-warning">Pending</span>
                <span class="ui-status-badge ui-status-danger">Disabled</span>
                <span class="ui-status-badge ui-status-neutral">Neutral</span>
                <span class="ui-status-badge ui-status-info">Info</span>
              </div>
            </div>
          </div>
        </section>

        <section class="space-y-4">
          <div>
            <h2 class="ui-panel-title">Tables</h2>
            <p class="ui-panel-subtitle">
              Tables use the shared wrapper, header, and cell classes from admin screens.
            </p>
          </div>

          <div class="ui-table-wrap">
            <table class="ui-table">
              <thead class="bg-gray-50 dark:bg-gray-800/70">
                <tr>
                  <th class="ui-table-head">Player</th>
                  <th class="ui-table-head">Status</th>
                  <th class="ui-table-head text-right">Games</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 bg-white dark:divide-gray-800 dark:bg-gray-900/40">
                <tr>
                  <td class="ui-table-cell font-medium text-gray-900 dark:text-white">Teebes</td>
                  <td class="ui-table-cell">
                    <span class="ui-status-badge ui-status-success">Approved</span>
                  </td>
                  <td class="ui-table-cell text-right text-gray-600 dark:text-gray-300">5</td>
                </tr>
                <tr>
                  <td class="ui-table-cell font-medium text-gray-900 dark:text-white">Default</td>
                  <td class="ui-table-cell">
                    <span class="ui-status-badge ui-status-warning">Pending</span>
                  </td>
                  <td class="ui-table-cell text-right text-gray-600 dark:text-gray-300">2</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { AlertTriangle, CheckCircle, Settings } from 'lucide-vue-next'

const tabs = ['Overview', 'Settings', 'System']
const activeTab = ref(tabs[0])
</script>
