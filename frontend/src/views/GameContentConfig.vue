<template>
  <div class="ui-page">
    <BaseModal :show="yamlModalOpen" @close="closeYamlModal">
      <div class="p-6">
        <div class="mb-4 flex items-start justify-between gap-4 pr-8">
          <div>
            <h2 class="text-xl font-semibold text-gray-900 dark:text-white">
              {{ yamlModalTitle }}
            </h2>
            <p v-if="yamlModalMeta" class="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {{ yamlModalMeta }}
            </p>
          </div>
          <button
            type="button"
            :disabled="yamlLoading || Boolean(yamlError) || !yamlContent"
            :class="[
              'ui-btn ui-btn-sm',
              copied
                ? 'border border-green-300 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950/40 dark:text-green-200'
                : 'ui-btn-secondary'
            ]"
            @click="copyYaml"
          >
            <Check v-if="copied" class="h-4 w-4" aria-hidden="true" />
            <Copy v-else class="h-4 w-4" aria-hidden="true" />
            {{ copied ? 'Copied' : 'Copy' }}
          </button>
        </div>

        <div v-if="yamlLoading" class="flex items-center justify-center gap-3 py-12 text-gray-500 dark:text-gray-400">
          <Loader2 class="h-5 w-5 animate-spin" aria-hidden="true" />
          <span>Loading YAML...</span>
        </div>
        <div v-else-if="yamlError" class="ui-alert ui-alert-error">
          {{ yamlError }}
        </div>
        <div v-else>
          <pre class="max-h-[60vh] overflow-auto rounded-lg bg-gray-900 p-4 text-sm text-gray-100 dark:bg-gray-950"><code>{{ yamlContent }}</code></pre>
          <p class="mt-3 text-xs text-gray-500 dark:text-gray-400">
            Copy this YAML into the ingestion tool to update this {{ selectedYamlResource?.type || 'resource' }} or use it as a template.
          </p>
        </div>
      </div>
    </BaseModal>

    <BaseModal
      :show="Boolean(aiDeckDraft)"
      panel-class="w-full sm:max-w-6xl"
      @close="closeAiDeckModal"
    >
      <form v-if="aiDeckDraft" class="min-h-[70vh]" @submit.prevent="saveAiDeck">
        <div class="border-b border-gray-200 p-6 pr-12 dark:border-gray-800">
          <h2 class="text-xl font-semibold text-gray-900 dark:text-white">
            {{ aiDeckDraft.id ? 'Edit AI Deck' : 'New AI Deck' }}
          </h2>
          <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
            {{ aiDeckDraftTotal }} cards
          </p>
        </div>

        <div class="space-y-6 p-6">
          <div class="grid gap-5 lg:grid-cols-4">
            <label class="block lg:col-span-2">
              <span class="ui-label">Name</span>
              <input
                v-model.trim="aiDeckDraft.name"
                type="text"
                class="ui-input mt-2"
                :disabled="aiDeckSaving"
              />
            </label>
            <label class="block">
              <span class="ui-label">Hero</span>
              <select
                v-model.number="aiDeckDraft.hero_id"
                class="ui-select mt-2"
                :disabled="aiDeckSaving"
              >
                <option
                  v-for="hero in heroes"
                  :key="hero.id"
                  :value="hero.id"
                >
                  {{ hero.name }}
                </option>
              </select>
            </label>
            <label class="block">
              <span class="ui-label">Strategy</span>
              <select
                v-model="aiDeckDraft.strategy"
                class="ui-select mt-2"
                :disabled="aiDeckSaving"
              >
                <option
                  v-for="strategy in aiStrategies"
                  :key="strategy"
                  :value="strategy"
                >
                  {{ strategy }}
                </option>
              </select>
            </label>
            <label class="block lg:col-span-3">
              <span class="ui-label">Description</span>
              <textarea
                v-model.trim="aiDeckDraft.description"
                rows="2"
                class="ui-input mt-2"
                :disabled="aiDeckSaving"
              />
            </label>
            <label class="block">
              <span class="ui-label">Draw mode</span>
              <select
                v-model="aiDeckDraft.draw_mode"
                class="ui-select mt-2"
                :disabled="aiDeckSaving"
                @change="handleAiDeckDrawModeChange"
              >
                <option value="shuffle">Shuffle</option>
                <option value="ordered">Ordered</option>
              </select>
            </label>
            <label class="block">
              <span class="ui-label">Starting hand</span>
              <input
                v-model.number="aiDeckDraft.starting_hand_size"
                type="number"
                min="0"
                class="ui-input mt-2"
                :disabled="aiDeckSaving"
              />
            </label>
            <label class="mt-7 flex items-center gap-3">
              <input
                v-model="aiDeckDraft.is_pve_opponent"
                type="checkbox"
                class="ui-checkbox"
                :disabled="aiDeckSaving"
              />
              <span class="ui-label">Visible in PvE</span>
            </label>
          </div>

          <div v-if="aiDeckDraftError" class="ui-alert ui-alert-warning">
            {{ aiDeckDraftError }}
          </div>

          <div class="grid gap-4 lg:grid-cols-[minmax(12rem,1fr)_minmax(14rem,1.4fr)_auto]">
            <label>
              <span class="ui-label">Search cards</span>
              <input
                v-model.trim="aiCardSearch"
                type="search"
                class="ui-input mt-2"
                placeholder="Name or slug"
                :disabled="aiDeckSaving"
              />
            </label>
            <label>
              <span class="ui-label">Add card</span>
              <select
                v-model="selectedAddCardId"
                class="ui-select mt-2"
                :disabled="aiDeckSaving || availableAiDeckCards.length === 0"
              >
                <option value="">Choose card</option>
                <option
                  v-for="card in availableAiDeckCards"
                  :key="card.id"
                  :value="String(card.id)"
                >
                  {{ card.name }} · {{ card.cost }} energy
                </option>
              </select>
            </label>
            <button
              type="button"
              class="ui-btn ui-btn-md ui-btn-secondary mt-7"
              :disabled="aiDeckSaving || !selectedAddCardId"
              @click="addCardToAiDeckDraft"
            >
              <Plus class="h-4 w-4" aria-hidden="true" />
              Add
            </button>
          </div>

          <div
            v-if="aiDeckDraft.draw_mode === 'ordered' && aiDeckDraft.draw_order.length === 0"
            class="ui-panel-muted text-sm text-gray-500 dark:text-gray-400"
          >
            No cards in this AI deck.
          </div>

          <div v-else-if="aiDeckDraft.draw_mode === 'ordered'" class="ui-table-wrap">
            <table class="ui-table">
              <thead class="bg-gray-50 dark:bg-gray-800/70">
                <tr>
                  <th class="ui-table-head w-20 text-right">#</th>
                  <th class="ui-table-head">Zone</th>
                  <th class="ui-table-head">Card</th>
                  <th class="ui-table-head">Type</th>
                  <th class="ui-table-head text-right">Cost</th>
                  <th class="ui-table-head text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 bg-white dark:divide-gray-800 dark:bg-gray-900/40">
                <tr v-for="(cardId, index) in aiDeckDraft.draw_order" :key="`${cardId}-${index}`">
                  <td class="ui-table-cell text-right font-semibold text-gray-900 dark:text-white">
                    {{ index + 1 }}
                  </td>
                  <td class="ui-table-cell">
                    <span
                      :class="[
                        'ui-status-badge',
                        index < normalizedDraftCount(aiDeckDraft.starting_hand_size)
                          ? 'ui-status-info'
                          : 'ui-status-neutral'
                      ]"
                    >
                      {{ index < normalizedDraftCount(aiDeckDraft.starting_hand_size) ? 'Opening hand' : 'Draw pile' }}
                    </span>
                  </td>
                  <td class="ui-table-cell">
                    <div class="font-medium text-gray-900 dark:text-white">
                      {{ orderedDraftCardName(cardId) }}
                    </div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">
                      {{ orderedDraftCardSlug(cardId) }}
                    </div>
                  </td>
                  <td class="ui-table-cell">
                    <span class="ui-status-badge ui-status-neutral capitalize">
                      {{ orderedDraftCardType(cardId) }}
                    </span>
                  </td>
                  <td class="ui-table-cell text-right font-semibold text-gray-900 dark:text-white">
                    {{ orderedDraftCardCost(cardId) }}
                  </td>
                  <td class="ui-table-cell text-right">
                    <div class="flex justify-end gap-2">
                      <button
                        type="button"
                        class="ui-btn ui-btn-xs ui-btn-secondary"
                        :disabled="aiDeckSaving || index === 0"
                        title="Move up"
                        @click="moveOrderedAiDeckCard(index, -1)"
                      >
                        <ArrowUp class="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                      <button
                        type="button"
                        class="ui-btn ui-btn-xs ui-btn-secondary"
                        :disabled="aiDeckSaving || index === aiDeckDraft.draw_order.length - 1"
                        title="Move down"
                        @click="moveOrderedAiDeckCard(index, 1)"
                      >
                        <ArrowDown class="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                      <button
                        type="button"
                        class="ui-btn ui-btn-xs ui-btn-danger"
                        :disabled="aiDeckSaving"
                        title="Remove"
                        @click="removeOrderedAiDeckCard(index)"
                      >
                        <Trash2 class="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-else-if="aiDeckDraft.cards.length === 0" class="ui-panel-muted text-sm text-gray-500 dark:text-gray-400">
            No cards in this AI deck.
          </div>

          <div v-else class="ui-table-wrap">
            <table class="ui-table">
              <thead class="bg-gray-50 dark:bg-gray-800/70">
                <tr>
                  <th class="ui-table-head">Card</th>
                  <th class="ui-table-head">Type</th>
                  <th class="ui-table-head text-right">Cost</th>
                  <th class="ui-table-head">Stats</th>
                  <th class="ui-table-head w-28 text-right">Count</th>
                  <th class="ui-table-head text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 bg-white dark:divide-gray-800 dark:bg-gray-900/40">
                <tr v-for="draftCard in aiDeckDraft.cards" :key="draftCard.card_id">
                  <td class="ui-table-cell">
                    <div class="font-medium text-gray-900 dark:text-white">
                      {{ draftCardName(draftCard) }}
                    </div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">
                      {{ draftCardSlug(draftCard) }}
                    </div>
                  </td>
                  <td class="ui-table-cell">
                    <span class="ui-status-badge ui-status-neutral capitalize">
                      {{ draftCardType(draftCard) }}
                    </span>
                  </td>
                  <td class="ui-table-cell text-right font-semibold text-gray-900 dark:text-white">
                    {{ draftCardCost(draftCard) }}
                  </td>
                  <td class="ui-table-cell text-gray-700 dark:text-gray-300">
                    {{ draftCardStats(draftCard) }}
                  </td>
                  <td class="ui-table-cell text-right">
                    <input
                      v-model.number="draftCard.count"
                      type="number"
                      min="1"
                      class="ui-input ml-auto w-20 text-right"
                      :disabled="aiDeckSaving"
                    />
                  </td>
                  <td class="ui-table-cell text-right">
                    <button
                      type="button"
                      class="ui-btn ui-btn-xs ui-btn-danger"
                      :disabled="aiDeckSaving"
                      @click="removeCardFromAiDeckDraft(draftCard.card_id)"
                    >
                      <Trash2 class="h-3.5 w-3.5" aria-hidden="true" />
                      Remove
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="sticky bottom-0 flex flex-col-reverse gap-3 border-t border-gray-200 bg-white p-4 shadow-[0_-8px_20px_rgba(15,23,42,0.06)] sm:flex-row sm:justify-end sm:px-6 dark:border-gray-800 dark:bg-gray-900 dark:shadow-[0_-8px_20px_rgba(0,0,0,0.24)]">
          <button
            type="button"
            class="ui-btn ui-btn-md ui-btn-secondary"
            :disabled="aiDeckSaving"
            @click="closeAiDeckModal"
          >
            Cancel
          </button>
          <button
            type="submit"
            class="ui-btn ui-btn-md ui-btn-primary"
            :disabled="aiDeckSaving || Boolean(aiDeckDraftError)"
          >
            <Loader2 v-if="aiDeckSaving" class="h-4 w-4 animate-spin" aria-hidden="true" />
            <Save v-else class="h-4 w-4" aria-hidden="true" />
            {{ aiDeckSaving ? 'Saving' : 'Save AI Deck' }}
          </button>
        </div>
      </form>
    </BaseModal>

    <main class="ui-page-container">
      <header class="ui-page-header-row">
        <div>
          <router-link
            :to="{ name: 'GameConfig', params: { slug } }"
            class="mb-3 inline-flex items-center gap-2 text-sm font-medium text-gray-500 transition hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <ArrowLeft class="h-4 w-4" aria-hidden="true" />
            Game Config
          </router-link>
          <h1 class="ui-page-title">Heroes & Cards</h1>
          <p class="ui-page-meta">{{ pageTitle }}</p>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <router-link
            :to="{ name: 'TitleEdit', params: { slug } }"
            class="ui-btn ui-btn-md ui-btn-secondary"
          >
            <FileCode2 class="h-4 w-4" aria-hidden="true" />
            Edit YAML
          </router-link>
          <router-link
            :to="{ name: 'CardCreate', params: { slug } }"
            class="ui-btn ui-btn-md ui-btn-primary"
          >
            <Plus class="h-4 w-4" aria-hidden="true" />
            New Card
          </router-link>
        </div>
      </header>

      <div v-if="loading" class="ui-panel min-h-64 items-center justify-center">
        <Loader2 class="h-6 w-6 animate-spin text-primary-600" aria-hidden="true" />
      </div>

      <div v-else-if="error" class="ui-alert ui-alert-error">
        {{ error }}
      </div>

      <div v-else class="space-y-8">
        <section class="grid gap-4 md:grid-cols-5">
          <div class="ui-panel-muted">
            <p class="text-sm text-gray-500 dark:text-gray-400">Heroes</p>
            <p class="ui-stat-value">{{ heroes.length }}</p>
          </div>
          <div class="ui-panel-muted">
            <p class="text-sm text-gray-500 dark:text-gray-400">Cards</p>
            <p class="ui-stat-value">{{ cards.length }}</p>
          </div>
          <div class="ui-panel-muted">
            <p class="text-sm text-gray-500 dark:text-gray-400">Collectible</p>
            <p class="ui-stat-value">{{ collectibleCardCount }}</p>
          </div>
          <div class="ui-panel-muted">
            <p class="text-sm text-gray-500 dark:text-gray-400">Hero scoped</p>
            <p class="ui-stat-value">{{ heroScopedCardCount }}</p>
          </div>
          <div class="ui-panel-muted">
            <p class="text-sm text-gray-500 dark:text-gray-400">AI Decks</p>
            <p class="ui-stat-value">{{ aiDecks.length }}</p>
          </div>
        </section>

        <div class="ui-tabs-shell">
          <div class="ui-tabs-scroll">
            <nav class="ui-tabs" aria-label="Content configuration sections">
              <button
                v-for="tab in tabs"
                :key="tab.id"
                type="button"
                :class="['ui-tab', activeTab === tab.id ? 'ui-tab-active' : 'ui-tab-inactive']"
                @click="activeTab = tab.id"
              >
                {{ tab.name }}
              </button>
            </nav>
          </div>
        </div>

        <section v-if="activeTab === 'heroes'" class="ui-panel">
          <div class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 class="ui-panel-title">Heroes</h2>
              <p class="ui-panel-subtitle">Latest hero templates for this title.</p>
            </div>
            <router-link
              :to="{ name: 'TitleEdit', params: { slug } }"
              class="ui-btn ui-btn-sm ui-btn-secondary self-start sm:self-auto"
            >
              <FileCode2 class="h-4 w-4" aria-hidden="true" />
              Edit Heroes
            </router-link>
          </div>

          <div v-if="heroes.length === 0" class="ui-panel-muted text-sm text-gray-500 dark:text-gray-400">
            No heroes have been created for this title.
          </div>

          <div v-else class="ui-table-wrap">
            <table class="ui-table">
              <thead class="bg-gray-50 dark:bg-gray-800/70">
                <tr>
                  <th class="ui-table-head">Hero</th>
                  <th class="ui-table-head">Health</th>
                  <th class="ui-table-head">Power</th>
                  <th class="ui-table-head">Faction</th>
                  <th class="ui-table-head text-right">Scoped cards</th>
                  <th class="ui-table-head text-right">Version</th>
                  <th class="ui-table-head text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 bg-white dark:divide-gray-800 dark:bg-gray-900/40">
                <tr v-for="hero in heroes" :key="hero.id">
                  <td class="ui-table-cell">
                    <div class="flex items-center gap-3">
                      <div class="flex h-10 w-10 flex-none items-center justify-center rounded-lg bg-gray-100 text-sm font-semibold text-gray-700 dark:bg-gray-800 dark:text-gray-200">
                        {{ hero.name.charAt(0).toUpperCase() }}
                      </div>
                      <div>
                        <div class="font-medium text-gray-900 dark:text-white">{{ hero.name }}</div>
                        <div class="text-xs text-gray-500 dark:text-gray-400">{{ hero.slug }}</div>
                      </div>
                    </div>
                  </td>
                  <td class="ui-table-cell font-semibold text-gray-900 dark:text-white">
                    {{ hero.health }}
                  </td>
                  <td class="ui-table-cell">
                    <div class="text-sm text-gray-900 dark:text-white">{{ heroPowerName(hero) }}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">
                      {{ heroPowerActionCount(hero) }} action{{ heroPowerActionCount(hero) === 1 ? '' : 's' }} - {{ heroPowerCost(hero) }} energy
                    </div>
                  </td>
                  <td class="ui-table-cell">
                    <span v-if="hero.faction_slug" class="ui-status-badge ui-status-info">
                      {{ hero.faction_slug }}
                    </span>
                    <span v-else class="text-sm text-gray-500 dark:text-gray-400">Common</span>
                  </td>
                  <td class="ui-table-cell text-right text-gray-700 dark:text-gray-300">
                    {{ scopedCardsForHero(hero).length }}
                  </td>
                  <td class="ui-table-cell text-right text-gray-500 dark:text-gray-400">
                    v{{ hero.version }}
                  </td>
                  <td class="ui-table-cell text-right">
                    <button
                      type="button"
                      class="ui-btn ui-btn-xs ui-btn-secondary"
                      @click="openYamlModal('hero', hero)"
                    >
                      <FileCode2 class="h-3.5 w-3.5" aria-hidden="true" />
                      YAML
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-else-if="activeTab === 'cards'" class="ui-panel">
          <div class="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h2 class="ui-panel-title">Cards</h2>
              <p class="ui-panel-subtitle">Latest card templates and their current hero scope.</p>
            </div>

            <div class="grid gap-3 sm:grid-cols-[minmax(14rem,1fr)_11rem_11rem] lg:w-[42rem]">
              <label>
                <span class="ui-label">Search</span>
                <input
                  v-model.trim="searchQuery"
                  type="search"
                  class="ui-input mt-2"
                  placeholder="Name or slug"
                />
              </label>
              <label>
                <span class="ui-label">Type</span>
                <select v-model="cardTypeFilter" class="ui-select mt-2">
                  <option value="all">All types</option>
                  <option value="creature">Creatures</option>
                  <option value="spell">Spells</option>
                </select>
              </label>
              <label>
                <span class="ui-label">Scope</span>
                <select v-model="scopeFilter" class="ui-select mt-2">
                  <option value="all">All scopes</option>
                  <option value="global">All heroes</option>
                  <option value="hero">Hero scoped</option>
                </select>
              </label>
            </div>
          </div>

          <div v-if="filteredCards.length === 0" class="ui-panel-muted text-sm text-gray-500 dark:text-gray-400">
            No cards match the current filters.
          </div>

          <div v-else class="ui-table-wrap">
            <table class="ui-table">
              <thead class="bg-gray-50 dark:bg-gray-800/70">
                <tr>
                  <th class="ui-table-head">Card</th>
                  <th class="ui-table-head">Type</th>
                  <th class="ui-table-head text-right">Cost</th>
                  <th class="ui-table-head">Stats</th>
                  <th class="ui-table-head">Hero scope</th>
                  <th class="ui-table-head">Collectible</th>
                  <th class="ui-table-head text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 bg-white dark:divide-gray-800 dark:bg-gray-900/40">
                <tr v-for="card in filteredCards" :key="card.id">
                  <td class="ui-table-cell">
                    <div class="font-medium text-gray-900 dark:text-white">{{ card.name }}</div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">{{ card.slug }}</div>
                  </td>
                  <td class="ui-table-cell">
                    <span class="ui-status-badge ui-status-neutral capitalize">
                      {{ card.card_type }}
                    </span>
                  </td>
                  <td class="ui-table-cell text-right font-semibold text-gray-900 dark:text-white">
                    {{ card.cost }}
                  </td>
                  <td class="ui-table-cell text-gray-700 dark:text-gray-300">
                    <span v-if="card.card_type === 'creature'">
                      {{ card.attack ?? 0 }} / {{ card.health ?? 0 }}
                    </span>
                    <span v-else class="text-gray-500 dark:text-gray-400">-</span>
                  </td>
                  <td class="ui-table-cell">
                    <span
                      :class="[
                        'ui-status-badge',
                        cardHeroSlugs(card).length ? 'ui-status-info' : 'ui-status-success'
                      ]"
                    >
                      {{ cardHeroScopeLabel(card) }}
                    </span>
                  </td>
                  <td class="ui-table-cell">
                    <span
                      :class="[
                        'ui-status-badge',
                        card.is_collectible === false ? 'ui-status-neutral' : 'ui-status-success'
                      ]"
                    >
                      {{ card.is_collectible === false ? 'No' : 'Yes' }}
                    </span>
                  </td>
                  <td class="ui-table-cell text-right">
                    <div class="flex flex-wrap justify-end gap-2">
                      <button
                        type="button"
                        class="ui-btn ui-btn-xs ui-btn-secondary"
                        @click="openYamlModal('card', card)"
                      >
                        <FileCode2 class="h-3.5 w-3.5" aria-hidden="true" />
                        YAML
                      </button>
                      <router-link
                        :to="{ name: 'CardDetails', params: { slug, cardSlug: card.slug } }"
                        class="ui-btn ui-btn-xs ui-btn-secondary"
                      >
                        View
                      </router-link>
                      <router-link
                        :to="{ name: 'CardEdit', params: { slug, cardSlug: card.slug } }"
                        class="ui-btn ui-btn-xs ui-btn-primary"
                      >
                        Edit
                      </router-link>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-else class="space-y-6">
          <div class="ui-panel">
            <div class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div class="ui-panel-heading">
                <Bot class="ui-panel-icon" aria-hidden="true" />
                <h2 class="ui-panel-title">AI Decks</h2>
              </div>
              <button
                type="button"
                class="ui-btn ui-btn-sm ui-btn-primary self-start sm:self-auto"
                @click="startNewAiDeck"
              >
                <Plus class="h-4 w-4" aria-hidden="true" />
                New AI Deck
              </button>
            </div>

            <div v-if="aiDecks.length === 0" class="ui-panel-muted text-sm text-gray-500 dark:text-gray-400">
              No AI decks have been created for this title.
            </div>

            <div v-else class="ui-table-wrap">
              <table class="ui-table">
                <thead class="bg-gray-50 dark:bg-gray-800/70">
                  <tr>
                    <th class="ui-table-head">Deck</th>
                    <th class="ui-table-head">Hero</th>
                    <th class="ui-table-head text-right">Cards</th>
                    <th class="ui-table-head">Strategy</th>
                    <th class="ui-table-head">Setup</th>
                    <th class="ui-table-head">PvE</th>
                    <th class="ui-table-head text-right">Actions</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-200 bg-white dark:divide-gray-800 dark:bg-gray-900/40">
                  <tr
                    v-for="deck in aiDecks"
                    :key="deck.id"
                    :class="selectedAiDeckId === deck.id ? 'bg-primary-50/60 dark:bg-primary-950/20' : ''"
                  >
                    <td class="ui-table-cell">
                      <div class="font-medium text-gray-900 dark:text-white">{{ deck.name }}</div>
                      <div class="text-xs text-gray-500 dark:text-gray-400">{{ deck.ai_player.name }}</div>
                    </td>
                    <td class="ui-table-cell text-gray-700 dark:text-gray-300">
                      {{ deck.hero.name }}
                    </td>
                    <td class="ui-table-cell text-right font-semibold text-gray-900 dark:text-white">
                      {{ deck.card_count }}
                    </td>
                    <td class="ui-table-cell">
                      <span class="ui-status-badge ui-status-neutral capitalize">
                        {{ deck.strategy }}
                      </span>
                    </td>
                    <td class="ui-table-cell">
                      <div class="flex flex-wrap gap-2">
                        <span
                          :class="[
                            'ui-status-badge capitalize',
                            deck.draw_mode === 'ordered' ? 'ui-status-info' : 'ui-status-neutral'
                          ]"
                        >
                          {{ deck.draw_mode }}
                        </span>
                        <span class="ui-status-badge ui-status-neutral">
                          Hand {{ deck.starting_hand_size }}
                        </span>
                      </div>
                    </td>
                    <td class="ui-table-cell">
                      <span
                        :class="[
                          'ui-status-badge',
                          deck.is_pve_opponent ? 'ui-status-success' : 'ui-status-neutral'
                        ]"
                      >
                        {{ deck.is_pve_opponent ? 'Visible' : 'Hidden' }}
                      </span>
                    </td>
                    <td class="ui-table-cell text-right">
                      <div class="flex flex-wrap justify-end gap-2">
                        <button
                          type="button"
                          class="ui-btn ui-btn-xs ui-btn-secondary"
                          @click="editAiDeck(deck)"
                        >
                          <Pencil class="h-3.5 w-3.5" aria-hidden="true" />
                          Edit
                        </button>
                        <button
                          type="button"
                          class="ui-btn ui-btn-xs ui-btn-danger"
                          :disabled="aiDeckSaving"
                          @click="archiveAiDeck(deck)"
                        >
                          <Trash2 class="h-3.5 w-3.5" aria-hidden="true" />
                          Archive
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  ArrowLeft,
  ArrowDown,
  ArrowUp,
  Bot,
  Check,
  Copy,
  FileCode2,
  Loader2,
  Pencil,
  Plus,
  Save,
  Trash2
} from 'lucide-vue-next'
import axios from '../config/api'
import BaseModal from '../components/modals/BaseModal.vue'
import { useNotificationStore } from '../stores/notifications'
import { useTitleStore } from '../stores/title'

interface TitleSummary {
  slug: string
  name: string
}

interface HeroConfig {
  id: number
  slug: string
  name: string
  description: string
  version: number
  health: number
  hero_power: {
    name?: string
    description?: string
    cost?: number
    actions?: unknown[]
  }
  spec: Record<string, unknown>
  faction_slug: string | null
  art_url: string | null
}

interface CardConfig {
  id: number
  slug: string
  name: string
  description: string
  version: number
  card_type: 'creature' | 'spell'
  cost: number
  attack: number | null
  health: number | null
  spec: Record<string, unknown>
  is_collectible: boolean
  faction_slug: string | null
  art_url: string | null
  hero_slugs?: string[]
  traits_with_data?: Array<{
    slug: string
    name: string
    data: Record<string, unknown>
  }>
}

interface ContentConfigResponse {
  title: TitleSummary
  heroes: HeroConfig[]
  cards: CardConfig[]
}

interface AIDeckConfig {
  deck_size_limit: number
  min_cards_in_deck: number
  deck_card_max_count: number
  hand_start_size: number
}

interface AIDeckCard {
  deck_card_id: number
  card_id: number
  card_slug: string
  name: string
  card_type: 'creature' | 'spell'
  cost: number
  attack: number | null
  health: number | null
  count: number
  is_collectible: boolean
  hero_slugs: string[]
}

interface AIDeck {
  id: number
  name: string
  description: string
  is_pve_opponent: boolean
  strategy: AIStrategy
  draw_mode: AIDeckDrawMode
  starting_hand_size: number
  draw_order: number[]
  ai_player: {
    id: number
    name: string
  }
  hero: {
    id: number
    slug: string
    name: string
    health: number
  }
  card_count: number
  cards: AIDeckCard[]
}

interface AIDeckListResponse {
  title: TitleSummary
  config: AIDeckConfig
  decks: AIDeck[]
}

type AIStrategy = 'rush' | 'control' | 'combo' | 'aggressive' | 'defensive'
type AIDeckDrawMode = 'shuffle' | 'ordered'

interface AIDeckDraftCard {
  card_id: number
  count: number
}

interface AIDeckDraft {
  id: number | null
  name: string
  description: string
  hero_id: number | null
  is_pve_opponent: boolean
  strategy: AIStrategy
  draw_mode: AIDeckDrawMode
  starting_hand_size: number
  draw_order: number[]
  cards: AIDeckDraftCard[]
}

type YamlResourceType = 'hero' | 'card'

interface YamlResourceSummary {
  type: YamlResourceType
  slug: string
  name: string
}

const tabs = [
  { id: 'heroes', name: 'Heroes' },
  { id: 'cards', name: 'Cards' },
  { id: 'ai-decks', name: 'AI Decks' }
] as const

type TabId = typeof tabs[number]['id']

const route = useRoute()
const titleStore = useTitleStore()
const notificationStore = useNotificationStore()

const aiStrategies: AIStrategy[] = ['rush', 'control', 'combo', 'aggressive', 'defensive']

const slug = computed(() => route.params.slug as string)
const loading = ref(true)
const error = ref<string | null>(null)
const content = ref<ContentConfigResponse | null>(null)
const activeTab = ref<TabId>('heroes')
const searchQuery = ref('')
const cardTypeFilter = ref<'all' | 'creature' | 'spell'>('all')
const scopeFilter = ref<'all' | 'global' | 'hero'>('all')
const aiDecks = ref<AIDeck[]>([])
const aiDeckConfig = ref<AIDeckConfig>({
  deck_size_limit: 30,
  min_cards_in_deck: 10,
  deck_card_max_count: 9,
  hand_start_size: 3
})
const selectedAiDeckId = ref<number | null>(null)
const aiDeckDraft = ref<AIDeckDraft | null>(null)
const aiDeckSaving = ref(false)
const aiCardSearch = ref('')
const selectedAddCardId = ref('')
const yamlModalOpen = ref(false)
const selectedYamlResource = ref<YamlResourceSummary | null>(null)
const yamlContent = ref('')
const yamlLoading = ref(false)
const yamlError = ref<string | null>(null)
const copied = ref(false)

const pageTitle = computed(() => content.value?.title.name || titleStore.currentTitle?.name || 'World')
const heroes = computed(() => content.value?.heroes || [])
const cards = computed(() => content.value?.cards || [])
const heroLookup = computed(() => new Map(heroes.value.map(hero => [hero.slug, hero])))
const heroById = computed(() => new Map(heroes.value.map(hero => [hero.id, hero])))
const cardById = computed(() => new Map(cards.value.map(card => [card.id, card])))
const selectedAiDeck = computed(() => (
  selectedAiDeckId.value == null
    ? null
    : aiDecks.value.find(deck => deck.id === selectedAiDeckId.value) || null
))
const yamlModalTitle = computed(() => (
  selectedYamlResource.value ? `${selectedYamlResource.value.name} YAML` : 'YAML Definition'
))
const yamlModalMeta = computed(() => {
  if (!selectedYamlResource.value) return ''
  const resourceType = selectedYamlResource.value.type === 'hero' ? 'Hero' : 'Card'
  return `${resourceType} - ${selectedYamlResource.value.slug}`
})

const collectibleCardCount = computed(() => (
  cards.value.filter(card => card.is_collectible !== false).length
))

const heroScopedCardCount = computed(() => (
  cards.value.filter(card => cardHeroSlugs(card).length > 0).length
))

const filteredCards = computed(() => {
  const query = searchQuery.value.toLowerCase()

  return cards.value.filter(card => {
    if (cardTypeFilter.value !== 'all' && card.card_type !== cardTypeFilter.value) {
      return false
    }

    const heroSlugs = cardHeroSlugs(card)
    if (scopeFilter.value === 'global' && heroSlugs.length > 0) return false
    if (scopeFilter.value === 'hero' && heroSlugs.length === 0) return false

    if (!query) return true
    return (
      card.name.toLowerCase().includes(query) ||
      card.slug.toLowerCase().includes(query)
    )
  })
})

const aiDeckDraftTotal = computed(() => (
  aiDeckDraft.value?.draw_mode === 'ordered'
    ? aiDeckDraft.value.draw_order.length
    : aiDeckDraft.value?.cards.reduce((total, card) => total + normalizedDraftCount(card.count), 0) || 0
))

const selectedDraftHero = computed(() => (
  aiDeckDraft.value?.hero_id ? heroById.value.get(aiDeckDraft.value.hero_id) || null : null
))

const selectedDraftCardIds = computed(() => new Set(
  aiDeckDraft.value?.cards.map(card => card.card_id) || []
))

const availableAiDeckCards = computed(() => {
  const query = aiCardSearch.value.toLowerCase()

  return cards.value
    .filter(card => aiDeckDraft.value?.draw_mode === 'ordered' || !selectedDraftCardIds.value.has(card.id))
    .filter(card => isCardAvailableForAiDraftHero(card))
    .filter(card => {
      if (!query) return true
      return (
        card.name.toLowerCase().includes(query) ||
        card.slug.toLowerCase().includes(query)
      )
    })
    .slice(0, 80)
})

const aiDeckDraftError = computed(() => {
  const draft = aiDeckDraft.value
  if (!draft) return ''
  if (!draft.name.trim()) return 'Name is required.'
  if (!draft.hero_id) return 'Hero is required.'
  const startingHandSize = normalizedDraftCount(draft.starting_hand_size)
  if (startingHandSize !== Number(draft.starting_hand_size)) {
    return 'Starting hand must be a whole number.'
  }
  if (draft.draw_mode === 'ordered' && startingHandSize > draft.draw_order.length) {
    return 'Starting hand cannot exceed the ordered deck size.'
  }

  for (const draftCard of draft.cards) {
    const card = cardById.value.get(draftCard.card_id)
    if (!card) return 'One or more cards no longer exist.'
    const count = normalizedDraftCount(draftCard.count)
    if (count < 1) return 'Card counts must be at least 1.'
    if (!isCardAvailableForAiDraftHero(card)) {
      return `${card.name} is not available to ${selectedDraftHero.value?.name || 'this hero'}.`
    }
  }
  for (const cardId of draft.draw_order) {
    const card = cardById.value.get(cardId)
    if (!card) return 'One or more cards no longer exist.'
    if (!isCardAvailableForAiDraftHero(card)) {
      return `${card.name} is not available to ${selectedDraftHero.value?.name || 'this hero'}.`
    }
  }

  return ''
})

const readStringArray = (value: unknown): string[] => {
  if (Array.isArray(value)) {
    return value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
  }
  if (typeof value === 'string' && value.trim()) {
    return [value.trim()]
  }
  return []
}

const cardHeroSlugs = (card: CardConfig): string[] => {
  const direct = readStringArray(card.hero_slugs)
  if (direct.length) return direct

  const spec = card.spec || {}
  const candidates = [
    spec.hero_slugs,
    spec.hero_slug,
    spec.allowed_heroes,
    spec.allowedHeroes,
    spec.heroes,
    spec.hero
  ]

  for (const candidate of candidates) {
    const slugs = readStringArray(candidate)
    if (slugs.length) return slugs
  }

  return []
}

const cardHeroScopeLabel = (card: CardConfig): string => {
  const heroSlugs = cardHeroSlugs(card)
  if (!heroSlugs.length) return 'All heroes'

  return heroSlugs
    .map(heroSlug => heroLookup.value.get(heroSlug)?.name || heroSlug)
    .join(', ')
}

const scopedCardsForHero = (hero: HeroConfig): CardConfig[] => (
  cards.value.filter(card => cardHeroSlugs(card).includes(hero.slug))
)

const normalizedDraftCount = (count: number): number => {
  const numericCount = Number(count)
  if (!Number.isFinite(numericCount)) return 0
  return Math.max(0, Math.trunc(numericCount))
}

const isCardAvailableForAiDraftHero = (card: CardConfig): boolean => {
  const hero = selectedDraftHero.value
  if (!hero) return true
  const heroSlugs = cardHeroSlugs(card)
  return heroSlugs.length === 0 || heroSlugs.includes(hero.slug)
}

const draftSourceCard = (draftCard: AIDeckDraftCard): CardConfig | undefined => (
  cardById.value.get(draftCard.card_id)
)

const draftSourceDeckCard = (draftCard: AIDeckDraftCard): AIDeckCard | undefined => (
  selectedAiDeck.value?.cards.find(card => card.card_id === draftCard.card_id)
)

const draftCardName = (draftCard: AIDeckDraftCard): string => (
  draftSourceCard(draftCard)?.name || draftSourceDeckCard(draftCard)?.name || 'Unknown card'
)

const draftCardSlug = (draftCard: AIDeckDraftCard): string => (
  draftSourceCard(draftCard)?.slug || draftSourceDeckCard(draftCard)?.card_slug || ''
)

const draftCardType = (draftCard: AIDeckDraftCard): string => (
  draftSourceCard(draftCard)?.card_type || draftSourceDeckCard(draftCard)?.card_type || 'card'
)

const draftCardCost = (draftCard: AIDeckDraftCard): number | string => (
  draftSourceCard(draftCard)?.cost ?? draftSourceDeckCard(draftCard)?.cost ?? '-'
)

const draftCardStats = (draftCard: AIDeckDraftCard): string => {
  const card = draftSourceCard(draftCard)
  const deckCard = draftSourceDeckCard(draftCard)
  const cardType = card?.card_type || deckCard?.card_type
  if (cardType !== 'creature') return '-'
  const attack = card?.attack ?? deckCard?.attack ?? 0
  const health = card?.health ?? deckCard?.health ?? 0
  return `${attack} / ${health}`
}

const orderedDraftSourceCard = (cardId: number): CardConfig | undefined => (
  cardById.value.get(cardId)
)

const orderedDraftSourceDeckCard = (cardId: number): AIDeckCard | undefined => (
  selectedAiDeck.value?.cards.find(card => card.card_id === cardId)
)

const orderedDraftCardName = (cardId: number): string => (
  orderedDraftSourceCard(cardId)?.name || orderedDraftSourceDeckCard(cardId)?.name || 'Unknown card'
)

const orderedDraftCardSlug = (cardId: number): string => (
  orderedDraftSourceCard(cardId)?.slug || orderedDraftSourceDeckCard(cardId)?.card_slug || ''
)

const orderedDraftCardType = (cardId: number): string => (
  orderedDraftSourceCard(cardId)?.card_type || orderedDraftSourceDeckCard(cardId)?.card_type || 'card'
)

const orderedDraftCardCost = (cardId: number): number | string => (
  orderedDraftSourceCard(cardId)?.cost ?? orderedDraftSourceDeckCard(cardId)?.cost ?? '-'
)

const expandedDrawOrderFromCards = (draftCards: AIDeckDraftCard[]): number[] => (
  draftCards.flatMap(card => Array(normalizedDraftCount(card.count)).fill(card.card_id))
)

const cardsFromDrawOrder = (drawOrder: number[]): AIDeckDraftCard[] => {
  const counts = new Map<number, number>()
  for (const cardId of drawOrder) {
    counts.set(cardId, (counts.get(cardId) || 0) + 1)
  }
  return Array.from(counts, ([card_id, count]) => ({ card_id, count }))
}

const syncCardsFromDrawOrder = (): void => {
  if (!aiDeckDraft.value) return
  aiDeckDraft.value.cards = cardsFromDrawOrder(aiDeckDraft.value.draw_order)
}

const aiDeckToDraft = (deck: AIDeck): AIDeckDraft => ({
  id: deck.id,
  name: deck.name,
  description: deck.description || '',
  hero_id: deck.hero.id,
  is_pve_opponent: deck.is_pve_opponent,
  strategy: deck.strategy || 'rush',
  draw_mode: deck.draw_mode || 'shuffle',
  starting_hand_size: Number.isFinite(Number(deck.starting_hand_size))
    ? Math.max(0, Math.trunc(Number(deck.starting_hand_size)))
    : 0,
  draw_order: Array.isArray(deck.draw_order) ? deck.draw_order.map(Number).filter(Number.isFinite) : [],
  cards: deck.cards.map(card => ({
    card_id: card.card_id,
    count: card.count
  }))
})

const applyAiDeckResponse = (response: AIDeckListResponse): void => {
  aiDeckConfig.value = response.config
  aiDecks.value = response.decks || []

  if (
    selectedAiDeckId.value != null &&
    !aiDecks.value.some(deck => deck.id === selectedAiDeckId.value)
  ) {
    selectedAiDeckId.value = null
    aiDeckDraft.value = null
  }
}

const upsertAiDeck = (deck: AIDeck): void => {
  const index = aiDecks.value.findIndex(existingDeck => existingDeck.id === deck.id)
  if (index >= 0) {
    aiDecks.value.splice(index, 1, deck)
  } else {
    aiDecks.value.push(deck)
  }
}

const editAiDeck = (deck: AIDeck): void => {
  selectedAiDeckId.value = deck.id
  aiDeckDraft.value = aiDeckToDraft(deck)
  selectedAddCardId.value = ''
  aiCardSearch.value = ''
}

const startNewAiDeck = (): void => {
  selectedAiDeckId.value = null
  selectedAddCardId.value = ''
  aiCardSearch.value = ''
  aiDeckDraft.value = {
    id: null,
    name: '',
    description: '',
    hero_id: heroes.value[0]?.id || null,
    is_pve_opponent: false,
    strategy: 'rush',
    draw_mode: 'shuffle',
    starting_hand_size: aiDeckConfig.value.hand_start_size,
    draw_order: [],
    cards: []
  }
}

const cancelAiDeckEdit = (): void => {
  aiDeckDraft.value = null
  selectedAiDeckId.value = null
  selectedAddCardId.value = ''
  aiCardSearch.value = ''
}

const closeAiDeckModal = (): void => {
  if (aiDeckSaving.value) return
  cancelAiDeckEdit()
}

const addCardToAiDeckDraft = (): void => {
  if (!aiDeckDraft.value || !selectedAddCardId.value) return
  const cardId = Number(selectedAddCardId.value)
  if (!Number.isFinite(cardId)) return

  if (aiDeckDraft.value.draw_mode === 'ordered') {
    aiDeckDraft.value.draw_order.push(cardId)
    syncCardsFromDrawOrder()
    selectedAddCardId.value = ''
    return
  }

  if (aiDeckDraft.value.cards.some(card => card.card_id === cardId)) return

  aiDeckDraft.value.cards.push({
    card_id: cardId,
    count: 1
  })
  selectedAddCardId.value = ''
}

const removeCardFromAiDeckDraft = (cardId: number): void => {
  if (!aiDeckDraft.value) return
  aiDeckDraft.value.cards = aiDeckDraft.value.cards.filter(card => card.card_id !== cardId)
  aiDeckDraft.value.draw_order = aiDeckDraft.value.draw_order.filter(orderedCardId => orderedCardId !== cardId)
}

const removeOrderedAiDeckCard = (index: number): void => {
  if (!aiDeckDraft.value) return
  aiDeckDraft.value.draw_order.splice(index, 1)
  syncCardsFromDrawOrder()
}

const moveOrderedAiDeckCard = (index: number, direction: -1 | 1): void => {
  if (!aiDeckDraft.value) return
  const nextIndex = index + direction
  if (nextIndex < 0 || nextIndex >= aiDeckDraft.value.draw_order.length) return
  const [cardId] = aiDeckDraft.value.draw_order.splice(index, 1)
  aiDeckDraft.value.draw_order.splice(nextIndex, 0, cardId)
  syncCardsFromDrawOrder()
}

const handleAiDeckDrawModeChange = (): void => {
  if (!aiDeckDraft.value) return
  if (aiDeckDraft.value.draw_mode === 'ordered') {
    aiDeckDraft.value.draw_order = expandedDrawOrderFromCards(aiDeckDraft.value.cards)
    syncCardsFromDrawOrder()
  }
}

const aiDeckPayload = (draft: AIDeckDraft) => ({
  name: draft.name.trim(),
  description: draft.description.trim(),
  hero_id: draft.hero_id,
  is_pve_opponent: draft.is_pve_opponent,
  strategy: draft.strategy,
  draw_mode: draft.draw_mode,
  starting_hand_size: normalizedDraftCount(draft.starting_hand_size),
  draw_order: draft.draw_mode === 'ordered' ? draft.draw_order : [],
  cards: draft.cards.map(card => ({
    card_id: card.card_id,
    count: normalizedDraftCount(card.count)
  }))
})

const heroPowerName = (hero: HeroConfig): string => {
  return hero.hero_power?.name || 'Power'
}

const heroPowerActionCount = (hero: HeroConfig): number => {
  return Array.isArray(hero.hero_power?.actions) ? hero.hero_power.actions.length : 0
}

const heroPowerCost = (hero: HeroConfig): number => {
  const cost = Number(hero.hero_power?.cost ?? 0)
  if (!Number.isFinite(cost)) return 0
  return Math.max(0, Math.trunc(cost))
}

const fetchContent = async (): Promise<void> => {
  try {
    loading.value = true
    error.value = null
    const [contentResponse, aiDeckResponse] = await Promise.all([
      axios.get<ContentConfigResponse>(`/builder/titles/${slug.value}/content/`),
      axios.get<AIDeckListResponse>(`/builder/titles/${slug.value}/ai-decks/`)
    ])
    content.value = contentResponse.data
    applyAiDeckResponse(aiDeckResponse.data)
  } catch (err) {
    console.error('Error loading content configuration:', err)
    error.value = 'Failed to load content configuration.'
    notificationStore.handleApiError(err as Error)
  } finally {
    loading.value = false
  }
}

const saveAiDeck = async (): Promise<void> => {
  if (!aiDeckDraft.value || aiDeckDraftError.value) return

  try {
    aiDeckSaving.value = true
    const payload = aiDeckPayload(aiDeckDraft.value)
    const response = aiDeckDraft.value.id
      ? await axios.patch<AIDeck>(
        `/builder/titles/${slug.value}/ai-decks/${aiDeckDraft.value.id}/`,
        payload
      )
      : await axios.post<AIDeck>(
        `/builder/titles/${slug.value}/ai-decks/`,
        payload
      )

    upsertAiDeck(response.data)
    selectedAiDeckId.value = response.data.id
    aiDeckDraft.value = aiDeckToDraft(response.data)
    notificationStore.success('AI deck saved')
  } catch (err) {
    console.error('Error saving AI deck:', err)
    notificationStore.handleApiError(err as Error)
  } finally {
    aiDeckSaving.value = false
  }
}

const archiveAiDeck = async (deck: AIDeck): Promise<void> => {
  if (!window.confirm(`Archive "${deck.name}"?`)) return

  try {
    aiDeckSaving.value = true
    await axios.delete(`/builder/titles/${slug.value}/ai-decks/${deck.id}/`)
    aiDecks.value = aiDecks.value.filter(existingDeck => existingDeck.id !== deck.id)
    if (selectedAiDeckId.value === deck.id) {
      cancelAiDeckEdit()
    }
    notificationStore.success('AI deck archived')
  } catch (err) {
    console.error('Error archiving AI deck:', err)
    notificationStore.handleApiError(err as Error)
  } finally {
    aiDeckSaving.value = false
  }
}

const yamlEndpoint = (resource: YamlResourceSummary): string => {
  const resourcePath = resource.type === 'hero' ? 'heroes' : 'cards'
  return `/builder/titles/${slug.value}/${resourcePath}/${resource.slug}/yaml/`
}

const openYamlModal = async (
  type: YamlResourceType,
  resource: HeroConfig | CardConfig
): Promise<void> => {
  const resourceSummary = {
    type,
    slug: resource.slug,
    name: resource.name
  }
  selectedYamlResource.value = resourceSummary
  yamlModalOpen.value = true
  yamlLoading.value = true
  yamlError.value = null
  yamlContent.value = ''
  copied.value = false

  try {
    const response = await axios.get<{ yaml: string }>(yamlEndpoint(resourceSummary))
    yamlContent.value = response.data.yaml
  } catch (err: any) {
    yamlError.value = err.response?.data?.error || err.message || 'Failed to load YAML.'
    console.error('Error loading YAML:', err)
  } finally {
    yamlLoading.value = false
  }
}

const closeYamlModal = (): void => {
  yamlModalOpen.value = false
  selectedYamlResource.value = null
  yamlContent.value = ''
  yamlError.value = null
  copied.value = false
}

const writeTextWithTextarea = (text: string): boolean => {
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.top = '-9999px'
  document.body.appendChild(textarea)
  textarea.focus()
  textarea.select()

  const copiedToClipboard = document.execCommand('copy')
  document.body.removeChild(textarea)

  return copiedToClipboard
}

const writeTextToClipboard = async (text: string): Promise<void> => {
  if (writeTextWithTextarea(text)) return

  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text)
    return
  }

  throw new Error('Unable to copy text.')
}

const copyYaml = async (): Promise<void> => {
  if (!yamlContent.value) return

  try {
    await writeTextToClipboard(yamlContent.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy YAML:', err)
    notificationStore.error('Failed to copy YAML.')
  }
}

onMounted(fetchContent)

watch(slug, () => {
  closeYamlModal()
  cancelAiDeckEdit()
  void fetchContent()
})
</script>
