<template>
    <div class="h-[100svh] flex flex-row justify-center relative" v-if="!loading">

        <!-- Game Over Overlay -->
        <GameOverOverlay
            v-if="showingGameOver"
            :game-over="gameOver"
            :viewer="viewer"
            :elo-change="gameState.elo_change"
            :game-type="currentGameType ?? undefined"
            :rematch-loading="rematchLoading"
            @close="showingGameOver = false"
            @rematch="handleRematch"
            @intro-signup="handleIntroSignup"
            @intro-retry="handleIntroRetry" />

        <!-- Normal Mode -->
        <main
            v-if="!overlay"
            ref="boardSurface"
            class="board relative isolate flex-1 flex flex-col max-w-md w-full overflow-hidden border-r border-l border-gray-700">

            <!-- Opponent Side -->
            <div class="side-b flex-1 flex flex-col">

                <!-- Header -->
                 <div class="h-24 flex flex-row justify-between border-b border-gray-700">
                    <!-- Enemy Hero-->
                    <div
                        class="h-full shrink-0"
                        :ref="(el) => setEntityElement(opposingHero?.hero_id, el)"
                        :class="opposingHero?.hero_id ? getCombatEntityClass(opposingHero.hero_id) : undefined"
                        :style="opposingHero?.hero_id ? getCombatEntityStyle(opposingHero.hero_id) : undefined">
                        <Hero
                            :hero="opposingHero"
                            :hero-art-url="opposingHeroArtUrl"
                            :hero-name="opposingHeroName"
                            :health="opposingHero?.health"
                            :active="gameState.active === topSide"
                            @click="handleClickOpposingHero"
                        />
                    </div>

                    <!-- Recent Updates -->
                    <div class="flex flex-1 flex-col p-2 justify-center items-center cursor-pointer" @click="handleClickUpdates">
                        <Update v-if="displayUpdates.length > 0" :update="displayUpdates[displayUpdates.length - 1]" />
                    </div>

                    <!-- Menu -->
                    <button
                        type="button"
                        class="w-24 h-full shrink-0 appearance-none bg-transparent flex flex-col justify-center items-center text-center border-l border-gray-700 relative transition-colors hover:text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-inset"
                        :class="{ 'z-50 bg-gray-900': isMulliganPhase }"
                        aria-label="Open game menu"
                        title="Open game menu"
                        @click="handleMenuClick">
                        <!-- WebSocket Status Indicator -->
                        <div class="flex items-center mb-1 absolute top-2 right-1" :title="`WebSocket: ${wsStatus}`">
                            <div
                                class="w-2 h-2 rounded-full mr-1"
                                :class="{
                                    'bg-green-500': wsStatus === 'connected',
                                    'bg-yellow-500 animate-pulse': wsStatus === 'connecting' || wsStatus === 'reconnecting',
                                    'bg-red-500': wsStatus === 'disconnected'
                                }"
                                :title="`WebSocket: ${wsStatus}`"
                            ></div>
                            <!-- <span class="text-xs text-gray-400" :title="`WebSocket: ${wsStatus}`">
                                {{ wsStatus === 'connected' ? '●' : wsStatus === 'reconnecting' ? '↻' : wsStatus === 'connecting' ? '...' : '○' }}
                            </span> -->
                        </div>
                        <span class="inline-block">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
                                <rect y="5" width="24" height="2" rx="1" fill="currentColor"/>
                                <rect y="11" width="24" height="2" rx="1" fill="currentColor"/>
                                <rect y="17" width="24" height="2" rx="1" fill="currentColor"/>
                            </svg>
                        </span>
                    </button>
                 </div>

                 <!-- Stats -->
                 <div class="flex flex-row justify-around border-b border-gray-700 p-2">
                    <div class="flex flex-col text-center">
                        <div class="text-gray-500">Deck</div>
                        <div>{{ opposingDeckSize }}</div>
                    </div>
                    <div class="flex flex-col text-center">
                        <div class="text-gray-500">Hand</div>
                        <div>{{ opposingHandSize }}</div>
                    </div>
                    <div class="flex flex-col text-center">
                        <div class="text-gray-500">Energy</div>
                        <div>{{ opposingEnergy }}/{{ opposingEnergyPool }}</div>
                    </div>
                 </div>

                 <!-- OPPONENT BOARD -->
                 <div class="opponent-board flex-1 flex flex-row bg-gray-800 items-center overflow-x-auto">
                    <div class="lane flex flex-row h-24 mx-auto space-x-2">
                        <div
                            v-for="creature in opposingBoard"
                            :key="creature.creature_id"
                            class="w-14 shrink-0"
                            :ref="(el) => setEntityElement(creature.creature_id, el)"
                            :class="getCombatEntityClass(creature.creature_id)"
                            :style="getCombatEntityStyle(creature.creature_id)">
                            <GameCard v-if="creature"
                                      class="cursor-pointer"
                                      :card="creature"
                                      @click="handleClickOpposingCreature(creature.creature_id)"
                                      compact in_lane/>
                        </div>
                    </div>
                 </div>
            </div>

            <!-- Mid Section -->
            <div class="flex flex-row justify-between border-gray-700 border-t border-b min-h-14">
                <div class="flex items-center justify-center ml-2">
                    Turn {{ gameState.turn }}
                    <span v-if="timeLeft !== null" class="text-gray-500 ml-2">
                        [ {{ timeLeftString }} ]
                    </span>
                </div>
                <GameButton
                    v-if="gameState.winner === 'none' && gameState.active === bottomSide && gameState.phase === 'main'"
                    variant="secondary"
                    class="m-2"
                    :class="{ 'ring-2 ring-primary-500': hasNoAvailableActions }"
                    :disabled="isAutoSwitchingGame"
                    @click="handleEndTurn">End Turn</GameButton>
                <div v-else-if="gameState.winner !== 'none'" class="flex items-center justify-center mr-4">
                    <span v-if="gameOver.winner === bottomSide">You win!</span>
                    <span v-else-if="gameOver.winner === topSide">You lose!</span>
                </div>
            </div>

            <!-- Viewer Side-->
            <div class="side-a flex-1 flex flex-col">
                <!-- VIEWER BOARD -->
                <div class="viewer-board flex-1 flex flex-row bg-gray-800 items-center overflow-x-auto">
                    <div class="lane flex flex-row h-24 mx-auto space-x-2">
                        <div
                            v-for="creature in ownBoard"
                            :key="creature.creature_id"
                            class="w-14 shrink-0"
                            :ref="(el) => setEntityElement(creature.creature_id, el)"
                            :class="getCombatEntityClass(creature.creature_id)"
                            :style="getCombatEntityStyle(creature.creature_id)">
                            <GameCard v-if="creature"
                                      class="cursor-pointer"
                                      :card="creature"
                                      @click="handleClickOwnCreature(creature.creature_id)"
                                      compact in_lane/>
                        </div>
                    </div>
                 </div>

                <!-- Stats -->
                 <div class="flex flex-row justify-around border-t border-gray-700 p-2">
                    <div class="flex flex-col text-center">
                        <div class="text-gray-500">Deck</div>
                        <div>{{ ownDeckSize }}</div>
                    </div>
                    <div class="flex flex-col text-center">
                        <div class="text-gray-500">Hand</div>
                        <div>{{ ownHandSize }}</div>
                    </div>
                    <div class="flex flex-col text-center">
                        <div class="text-gray-500">Energy</div>
                        <div>{{ ownEnergy }}/{{ ownEnergyPool }}</div>
                    </div>
                 </div>

                <!-- Footer -->
                <div class="h-24 flex flex-row border-t border-gray-700">
                    <!-- Viewer Hero -->
                    <div
                        class="h-full shrink-0"
                        :ref="(el) => setEntityElement(ownHero?.hero_id, el)"
                        :class="ownHero?.hero_id ? getCombatEntityClass(ownHero.hero_id) : undefined"
                        :style="ownHero?.hero_id ? getCombatEntityStyle(ownHero.hero_id) : undefined">
                        <Hero
                            :hero="ownHero"
                            :hero-art-url="ownHeroArtUrl"
                            :hero-name="ownHeroName"
                            :health="ownHero?.health"
                            :active="gameState.active === bottomSide"
                            :opacity="!canUseHero"
                            @click="handleClickOwnHero"
                        />
                    </div>

                    <!-- Hand -->
                    <div class="hand min-w-0 overflow-x-auto flex flex-row flex-nowrap flex-grow items-center space-x-2 ml-2">
                        <div v-for="card_id in ownHand"
                             :key="card_id+'else'"
                             class="w-14 flex-none">
                            <GameCard v-if="get_card(card_id)"
                                class="cursor-pointer"
                                :card="get_card(card_id)!"
                                :active="isHandCardActive(card_id)"
                                @click="handleClickHandCard(card_id)"
                                compact />
                        </div>
                    </div>
                </div>
            </div>

            <!-- Mulligan Overlay -->
            <div
                v-if="isMulliganPhase"
                class="absolute inset-0 z-40 flex items-center justify-center bg-gray-950/85 p-4">
                <div class="w-full max-w-sm rounded-lg border border-gray-700 bg-gray-900 p-4 shadow-2xl">
                    <div class="mb-4 text-center">
                        <div class="text-lg font-semibold text-white">Opening Hand</div>
                        <div class="mt-1 text-sm text-gray-400">
                            <span v-if="!ownMulliganDone">Select cards to replace.</span>
                            <span v-else>Waiting for opponent.</span>
                        </div>
                    </div>

                    <div class="flex justify-center gap-3">
                        <button
                            v-for="cardId in mulliganCards"
                            :key="`mulligan-${cardId}`"
                            type="button"
                            class="relative w-20 shrink-0 rounded-lg transition-transform"
                            :class="{
                                'scale-[1.03]': isMulliganCardSelected(cardId),
                                'opacity-60': ownMulliganDone || mulliganSubmitting
                            }"
                            :disabled="ownMulliganDone || mulliganSubmitting"
                            @click="toggleMulliganCard(cardId)">
                            <GameCard
                                v-if="get_card(cardId)"
                                :card="get_card(cardId)!"
                                :active="isMulliganCardSelected(cardId)"
                                compact />
                        </button>
                    </div>

                    <div
                        v-if="!ownMulliganDone"
                        class="mt-5 flex items-center justify-between gap-3">
                        <div class="text-sm text-gray-400">
                            {{ selectedMulliganCount }} selected
                        </div>
                        <GameButton
                            variant="primary"
                            :disabled="mulliganSubmitting"
                            @click="handleSubmitMulligan">
                            {{ mulliganSubmitting ? 'Submitting' : selectedMulliganCount > 0 ? 'Replace Selected' : 'Keep Hand' }}
                        </GameButton>
                    </div>
                    <div v-else class="mt-5 text-center text-sm text-gray-400">
                        Hand submitted.
                    </div>
                </div>
            </div>

            <CombatAnimationLayer
                v-if="activeCombatAnimation"
                :key="activeCombatAnimation.key"
                :animation="activeCombatAnimation" />
            <div
                v-if="playedSpellCards.length > 0"
                class="played-spell-layer pointer-events-none absolute inset-0 z-30 overflow-hidden"
                aria-hidden="true">
                <div
                    v-for="playedSpell in playedSpellCards"
                    :key="playedSpell.key"
                    class="played-spell-card"
                    :class="[
                        playedSpell.side === bottomSide ? 'played-spell-card--bottom' : 'played-spell-card--top',
                        { 'is-leaving': playedSpell.leaving }
                    ]"
                    :style="getPlayedSpellCardStyle(playedSpell.side)">
                    <GameCard :card="playedSpell.card" compact />
                </div>
            </div>
            <CombatValueBursts
                v-if="combatValueBursts.length > 0"
                :bursts="combatValueBursts" />

        </main>

        <!-- Overlay Mode -->
         <main v-else class="board flex-1 flex flex-col max-w-md w-full border-r border-l border-gray-700">
            <!-- Header -->
            <OverlayHeader :text="overlayTitle" @close="closeOverlay" />

            <!-- Entity Detail Overlay -->
            <EntityDetail
                v-if="overlay === 'entity_detail' && selectedEntity"
                :entity-type="selectedEntity.type"
                :entity-id="selectedEntity.id"
                :is-owned="selectedEntity.isOwned ?? true"
                :card="selectedEntity.type === 'card' ? get_card(selectedEntity.id) : null"
                :creature="selectedEntity.type === 'creature' ? get_creature(selectedEntity.id) : null"
                :hero="selectedEntity.type === 'hero' ? getHero(selectedEntity.id) : null"
                :title-slug="titleStore.titleSlug ?? undefined"
                @close="closeOverlay"
                @place-creature="handlePlaceCreature"
                @cast-spell="handleCastSpell"
                @attack="handleAttack"
                @use-hero="handleUseHero"
            />

            <!-- Creature Placement Overlay -->
            <PlaceCreature
                v-if="overlay === 'place_creature'"
                :game-state="gameState"
                :card-id="selectedCardId"
                :own-board="ownBoard"
                :own-energy="ownEnergy"
                :title-slug="titleStore.titleSlug ?? undefined"
                @placement-selected="onPlacementSelected"
                @close="closeOverlay"
            />

            <!-- Target Selection Overlay -->
            <Target
                v-if="overlay === 'select_target' && targetingState"
                :opposing-board="opposingBoard"
                :opposing-hero="opposingHero"
                :own-board="ownBoard"
                :own-hero="ownHero"
                :allowed-target-types="targetingState.allowedTypes"
                :target-scope="targetingState.scope"
                :source-card="targetingState.sourceCard"
                :error-message="targetingState.errorMessage"
                :title="targetingState.title"
                :title-slug="titleStore.titleSlug ?? undefined"
                :bypass-taunt="targetingState.bypassTaunt"
                @target-selected="onTargetSelected"
                @cancelled="closeOverlay"
            />

            <!-- Menu Overlay -->
            <GameMenu
                v-if="overlay === 'menu'"
                :can-edit-title="canEditTitle ?? false"
                :show-extend-time="canShowExtendTime"
                :title-slug="titleStore.titleSlug ?? undefined"
                :game-over="gameOver.isGameOver"
                :is-intro-game="isIntroGame"
                :next-game="nextGame"
                @click-updates="handleClickUpdates"
                @click-how-to-play="handleClickHowToPlay"
                @click-extend-time="handleClickExtendTime"
                @click-debug="handleClickDebug"
            />

            <!-- How To Play Overlay -->
            <div v-if="overlay === 'how_to_play'" class="flex-1 min-h-0 overflow-y-auto">
                <TitleHelp :show-title="false" />
            </div>

            <!-- Updates Overlay -->
            <div v-if="overlay === 'updates'" class="flex-1 min-h-0">
                <UpdatesList :updates="displayUpdates" />
            </div>

            <!-- Debug Overlay -->
            <DebugOverlay v-if="overlay === 'debug'" :game-id="gameId" />

        </main>

    </div>

    <!-- Loading Screen -->
    <div class="min-h-screen flex flex-row justify-center" v-else>
        <div class="flex flex-col items-center justify-center">
            <div class="text-2xl font-bold">Loading...</div>
        </div>
    </div>

    <div
        v-if="autoSwitchTarget && !isIntroGame"
        class="pointer-events-auto fixed inset-0 z-[100] flex items-center justify-center bg-gray-950/55 px-6 backdrop-blur-[2px]"
        aria-live="polite">
        <div class="next-game-transition w-full max-w-xs border border-primary-500/40 bg-gray-950/95 px-5 py-4 text-center shadow-2xl">
            <div class="text-sm font-semibold uppercase tracking-[0.18em] text-primary-400">
                Next game
            </div>
            <div class="mt-2 truncate text-lg font-semibold text-white">
                {{ autoSwitchTarget.name }}
            </div>
            <div class="mt-4 h-1 overflow-hidden bg-gray-800">
                <div class="next-game-progress h-full bg-primary-500"></div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { watch, computed, ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { CardInPlay, Creature, Side } from '../types/game'
import { useAuthStore } from '../stores/auth'
import { useTitleStore } from '../stores/title'
import { useGameStore } from '../stores/game'
import { storeToRefs } from 'pinia'

import axios from '../config/api'
import { useNotificationStore } from '../stores/notifications'
import { startIntroScenario } from '../services/introScenario'
import GameCard from '../components/game/GameCard.vue'
import GameButton from '../components/ui/GameButton.vue'
// Board Components
import EntityDetail from '../components/game/board/EntityDetail.vue'
import PlaceCreature from '../components/game/board/PlaceCreature.vue'
import Target from '../components/game/board/Target.vue'
import GameOverOverlay from '../components/game/board/GameOverOverlay.vue'
import Update from '../components/game/board/Update.vue'
import UpdatesList from '../components/game/board/UpdatesList.vue'
import OverlayHeader from '../components/game/board/OverlayHeader.vue'
import DebugOverlay from '../components/game/board/DebugOverlay.vue'
import Hero from '../components/game/board/Hero.vue'
import GameMenu from '../components/game/board/GameMenu.vue'
import CombatAnimationLayer from '../components/game/board/CombatAnimationLayer.vue'
import CombatValueBursts from '../components/game/board/CombatValueBursts.vue'
import TitleHelp from '../components/title/TitleHelp.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const titleStore = useTitleStore()
const gameStore = useGameStore()

// Get reactive refs from the store
const {
  loading,
  gameState,
  gameOver,
  viewer,
  ownHero,
  ownHeroName,
  ownHandSize,
  ownDeckSize,
  ownHand,
  ownEnergy,
  ownEnergyPool,
  ownBoard,
  opposingHero,
  opposingHeroName,
  opposingHandSize,
  opposingDeckSize,
  opposingEnergy,
  opposingEnergyPool,
  opposingBoard,
  topSide,
  bottomSide,
  displayUpdates,
  liveUpdateBatch,
  liveUpdateBatchId,
  canUseHero,
  wsStatus,
  currentGameType
} = storeToRefs(gameStore)

const isIntroGame = computed(() => {
    return currentGameType.value === 'intro' || route.query.intro === '1'
})

// Get hero art URLs
const ownHeroArtUrl = computed(() => {
    if (!ownHero.value) {
        return null
    }
    const hero = ownHero.value as any
    if (hero.art_url) {
        return hero.art_url as string
    }
    return null
})

const opposingHeroArtUrl = computed(() => {
    if (!opposingHero.value) {
        return null
    }
    const hero = opposingHero.value as any
    if (hero.art_url) {
        return hero.art_url as string
    }
    return null
})


// Overlay Types
type OverlayType = 'entity_detail' | 'place_creature' | 'select_target' | 'menu' | 'updates' | 'how_to_play' | 'debug' | null

interface ActiveGameSummary {
    id: number
    name: string
    type: 'pve' | 'ranked' | 'friendly' | 'intro'
    is_user_turn: boolean
}

// Local UI state
const overlay = ref<OverlayType>(null)
const overlayTitle = ref<string>('')
const activeGames = ref<ActiveGameSummary[]>([])
const autoSwitchTarget = ref<ActiveGameSummary | null>(null)
const autoSwitchLookupInFlight = ref(false)

// Entity selection state (for detail view)
interface SelectedEntity {
    type: 'card' | 'creature' | 'hero'
    id: string
    isOwned?: boolean  // Whether this entity belongs to the current player
}
const selectedEntity = ref<SelectedEntity | null>(null)

// Card selection for placement
const selectedCardId = ref<string | null>(null)

// Targeting state
interface TargetingState {
    sourceType: 'creature' | 'hero' | 'spell' | 'battlecry'
    sourceId: string
    allowedTypes: 'creature' | 'hero' | 'both'
    scope: 'enemy' | 'friendly' | 'any'
    sourceCard: CardInPlay | Creature | null
    errorMessage: string | null
    title: string
    bypassTaunt?: boolean
}
const targetingState = ref<TargetingState | null>(null)

// Pending play context when battlecry target is required
const pendingPlay = ref<{ card_id: string; position: number } | null>(null)

interface DamageUpdate {
    type: 'update_damage'
    side: Side
    source_type: 'card' | 'hero' | 'board' | 'creature'
    source_id: string
    target_type: 'card' | 'hero' | 'creature'
    target_id: string
    damage: number
    is_retaliation?: boolean
}

interface PlayCardUpdate {
    type: 'update_play_card'
    side: Side
    source_type: 'card'
    source_id: string
    card_id: string
    position: number
}

interface HealUpdate {
    type: 'update_heal'
    side: Side
    source_type: 'card' | 'hero' | 'board' | 'creature'
    source_id: string
    target_type: 'card' | 'hero' | 'creature'
    target_id: string
    amount: number
}

interface CombatPoint {
    x: number
    y: number
}

interface CombatAnimationState {
    key: number
    kind: 'damage' | 'heal' | 'spell-damage'
    sourceId: string
    targetId: string
    source: CombatPoint
    target: CombatPoint
    value: number
    isRetaliation: boolean
}

interface CombatValueBurst {
    key: number
    kind: 'damage' | 'heal'
    value: number
    x: number
    y: number
}

interface PlayedSpellCard {
    key: number
    cardId: string
    side: Side
    card: CardInPlay
    leaving: boolean
}

const showingGameOver = ref(false)
const rematchLoading = ref(false)
const boardSurface = ref<HTMLElement | null>(null)
const activeCombatAnimation = ref<CombatAnimationState | null>(null)
const combatValueBursts = ref<CombatValueBurst[]>([])
const playedSpellCards = ref<PlayedSpellCard[]>([])
const mulliganSelectedCardIds = ref<string[]>([])
const mulliganSubmitting = ref(false)

const combatAnimationQueue: CombatAnimationState[] = []
const entityElements = new Map<string, HTMLElement>()
const entityFrames = new Map<string, DOMRect>()
const combatValueBurstTimeouts = new Map<number, number>()
const playedSpellCardTimeouts = new Map<string, number>()
const playedSpellCardExitTimeouts = new Map<string, number>()

let combatAnimationKey = 0
let combatAnimationTimeout: number | null = null
let combatValueBurstKey = 0
let playedSpellCardKey = 0
let autoSwitchNavigateTimeout: number | null = null
let autoSwitchClearTimeout: number | null = null

const COMBAT_ENTITY_LUNGE = 14
const COMBAT_ENTITY_RECOIL = 10
const HEAL_ENTITY_DRIFT = 6
const SPELL_ENTITY_PULSE = 8
const COMBAT_ANIMATION_DURATION_MS = 620
const COMBAT_VALUE_BURST_DURATION_MS = 2200
const PLAYED_SPELL_CARD_CENTER_OFFSET_PX = 76
const PLAYED_SPELL_CARD_FLOAT_OFFSET_PX = 12
const PLAYED_SPELL_CARD_DURATION_MS = 1700
const PLAYED_SPELL_CARD_EXIT_MS = 260
const PLAYED_SPELL_CARD_AFTER_ANIMATION_MS = 400
const AUTO_SWITCH_NAVIGATE_MS = 760
const AUTO_SWITCH_CLEAR_MS = 520

const title = computed(() => titleStore.currentTitle)

const isMulliganPhase = computed(() => gameState.value.phase === 'mulligan')

const ownMulliganDone = computed(() => {
    if (!viewer.value) return false
    return Boolean(gameState.value.mulligan_done?.[viewer.value])
})

const mulliganCards = computed(() => {
    if (!viewer.value) return []
    if (ownMulliganDone.value) {
        return ownHand.value
    }
    const options = gameState.value.mulligan_options?.[viewer.value]
    if (options !== undefined) {
        return options
    }
    return ownHand.value.slice(0, 3)
})

const selectedMulliganCount = computed(() => mulliganSelectedCardIds.value.length)

// Check if user can edit this title (for debug features)
const canEditTitle = computed(() => {
  return authStore.isAuthenticated &&
         title.value &&
         title.value.can_edit === true
})

const canShowExtendTime = computed(() => {
  return currentGameType.value === 'ranked'
})

// Check if user has no available actions (should highlight End Turn)
const hasNoAvailableActions = computed(() => {
  // Only relevant during player's turn in main phase
  if (gameState.value.active !== bottomSide.value) return false
  if (gameState.value.phase !== 'main') return false

  // Check if any card in hand can be played
  const hand = ownHand.value || []
  const energy = ownEnergy.value || 0
  const canPlayAnyCard = hand.some(cardId => {
    const card = get_card(cardId)
    return card && card.cost <= energy
  })
  if (canPlayAnyCard) return false

  // Check if any creature on board can attack
  const board = ownBoard.value || []
  const canAttackWithAny = board.some(
    creature => !creature.exhausted && creature.attack > 0
  )
  if (canAttackWithAny) return false

  // Check if hero power can be used
  if (canUseHero.value) return false

  // No actions available
  return true
})

// Game ID for debug overlay
const gameId = computed(() => route.params.game_id as string)

const nextGame = computed(() => {
    if (isIntroGame.value) {
        return null
    }
    return getNextGame(activeGames.value)
})

const isAutoSwitchingGame = computed(() => autoSwitchLookupInFlight.value || autoSwitchTarget.value !== null)

function getNextGame(games: ActiveGameSummary[]): ActiveGameSummary | null {
    const currentGameId = Number(gameId.value)
    return games.find(game =>
        game.is_user_turn && game.id !== currentGameId
    ) ?? null
}

// Time control countdown
const currentTime = ref(Date.now())

const timeLeft = computed(() => {
    if (!gameState.value.time_per_turn || gameState.value.time_per_turn === 0) {
        return null
    }

    if (!gameState.value.turn_expires) {
        return null
    }

    const expires = new Date(gameState.value.turn_expires).getTime()
    const remaining = Math.max(0, Math.floor((expires - currentTime.value) / 1000))
    return remaining
})

const timeLeftString = computed(() => {
    const left = timeLeft.value
    if (left === null) {
        return ''
    }

    const hours = Math.floor(left / 3600)
    const minutes = Math.floor((left % 3600) / 60)
    const seconds = left % 60

    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
    } else {
        return `${minutes}:${seconds.toString().padStart(2, '0')}`
    }
})

const setEntityElement = (entityId: string | undefined, element: Element | null) => {
    if (!entityId) return

    if (element instanceof HTMLElement) {
        entityElements.set(entityId, element)
        entityFrames.set(entityId, element.getBoundingClientRect())
        return
    }

    entityElements.delete(entityId)
}

const syncEntityFrames = () => {
    for (const [entityId, element] of entityElements.entries()) {
        entityFrames.set(entityId, element.getBoundingClientRect())
    }
}

const getEntityCenter = (entityId: string): CombatPoint | null => {
    const board = boardSurface.value
    if (!board) return null

    const liveRect = entityElements.get(entityId)?.getBoundingClientRect()
    const rect = liveRect ?? entityFrames.get(entityId)
    if (!rect) return null

    entityFrames.set(entityId, rect)

    const boardRect = board.getBoundingClientRect()
    return {
        x: rect.left - boardRect.left + (rect.width / 2),
        y: rect.top - boardRect.top + (rect.height / 2)
    }
}

const clearCombatAnimationTimeout = () => {
    if (combatAnimationTimeout !== null) {
        clearTimeout(combatAnimationTimeout)
        combatAnimationTimeout = null
    }
}

const clearCombatValueBurstTimeouts = () => {
    for (const timeoutId of combatValueBurstTimeouts.values()) {
        clearTimeout(timeoutId)
    }
    combatValueBurstTimeouts.clear()
}

const clearPlayedSpellCardTimeouts = () => {
    for (const timeoutId of playedSpellCardTimeouts.values()) {
        clearTimeout(timeoutId)
    }
    for (const timeoutId of playedSpellCardExitTimeouts.values()) {
        clearTimeout(timeoutId)
    }
    playedSpellCardTimeouts.clear()
    playedSpellCardExitTimeouts.clear()
}

const resetCombatAnimations = () => {
    clearCombatAnimationTimeout()
    activeCombatAnimation.value = null
    combatAnimationQueue.length = 0
    clearCombatValueBurstTimeouts()
    combatValueBursts.value = []
    clearPlayedSpellCardTimeouts()
    playedSpellCards.value = []
}

const playNextCombatAnimation = () => {
    if (activeCombatAnimation.value || combatAnimationQueue.length === 0) {
        return
    }

    activeCombatAnimation.value = combatAnimationQueue.shift() ?? null
    if (!activeCombatAnimation.value) {
        return
    }

    clearCombatAnimationTimeout()
    combatAnimationTimeout = window.setTimeout(() => {
        activeCombatAnimation.value = null
        combatAnimationTimeout = null
        playNextCombatAnimation()
    }, COMBAT_ANIMATION_DURATION_MS)
}

const isCombatDamageUpdate = (update: any): update is DamageUpdate => {
    if (update?.type !== 'update_damage') {
        return false
    }

    const validSource = update.source_type === 'hero' || update.source_type === 'creature'
    const validTarget = update.target_type === 'hero' || update.target_type === 'creature' || update.target_type === 'card'

    return validSource && validTarget && Boolean(update.source_id) && Boolean(update.target_id)
}

const isSpellDamageUpdate = (update: DamageUpdate) => {
    if (update.source_type !== 'card') {
        return false
    }

    const sourceCard = get_card(update.source_id)
    return sourceCard?.card_type === 'spell'
}

const isSpellHealUpdate = (update: HealUpdate) => {
    if (update.source_type !== 'card') {
        return false
    }

    const sourceCard = get_card(update.source_id)
    return sourceCard?.card_type === 'spell'
}

const isSpellPlayUpdate = (update: any): update is PlayCardUpdate => {
    if (update?.type !== 'update_play_card' || !update.card_id) {
        return false
    }

    const card = get_card(update.card_id)
    return card?.card_type === 'spell'
}

const removePlayedSpellCard = (cardId: string) => {
    const timeoutId = playedSpellCardTimeouts.get(cardId)
    if (timeoutId !== undefined) {
        clearTimeout(timeoutId)
        playedSpellCardTimeouts.delete(cardId)
    }

    const exitTimeoutId = playedSpellCardExitTimeouts.get(cardId)
    if (exitTimeoutId !== undefined) {
        clearTimeout(exitTimeoutId)
        playedSpellCardExitTimeouts.delete(cardId)
    }

    playedSpellCards.value = playedSpellCards.value.filter((playedSpell) => playedSpell.cardId !== cardId)
}

const hidePlayedSpellCard = (cardId: string) => {
    playedSpellCardTimeouts.delete(cardId)

    const playedSpell = playedSpellCards.value.find((entry) => entry.cardId === cardId)
    if (!playedSpell || playedSpell.leaving) {
        return
    }

    playedSpellCards.value = playedSpellCards.value.map((entry) =>
        entry.cardId === cardId ? { ...entry, leaving: true } : entry
    )

    const exitTimeoutId = window.setTimeout(() => {
        removePlayedSpellCard(cardId)
    }, PLAYED_SPELL_CARD_EXIT_MS)
    playedSpellCardExitTimeouts.set(cardId, exitTimeoutId)
}

const showPlayedSpellCard = (
    cardId: string,
    side: Side,
    durationMs: number = PLAYED_SPELL_CARD_DURATION_MS
) => {
    const card = get_card(cardId)
    if (!card || card.card_type !== 'spell') {
        return
    }

    const existingExitTimeoutId = playedSpellCardExitTimeouts.get(cardId)
    if (existingExitTimeoutId !== undefined) {
        clearTimeout(existingExitTimeoutId)
        playedSpellCardExitTimeouts.delete(cardId)
    }

    const existingIndex = playedSpellCards.value.findIndex((entry) => entry.cardId === cardId)
    if (existingIndex >= 0) {
        playedSpellCards.value = playedSpellCards.value.map((entry) =>
            entry.cardId === cardId ? { ...entry, side, card, leaving: false } : entry
        )
    } else {
        playedSpellCards.value = [
            ...playedSpellCards.value,
            {
                key: ++playedSpellCardKey,
                cardId,
                side,
                card,
                leaving: false
            }
        ]
    }

    const existingTimeoutId = playedSpellCardTimeouts.get(cardId)
    if (existingTimeoutId !== undefined) {
        clearTimeout(existingTimeoutId)
    }

    const timeoutId = window.setTimeout(() => {
        hidePlayedSpellCard(cardId)
    }, Math.max(durationMs, PLAYED_SPELL_CARD_DURATION_MS))
    playedSpellCardTimeouts.set(cardId, timeoutId)
}

const isHealUpdate = (update: any): update is HealUpdate => {
    if (update?.type !== 'update_heal') {
        return false
    }

    const validTarget = update.target_type === 'hero' || update.target_type === 'creature' || update.target_type === 'card'
    return validTarget && Boolean(update.target_id)
}

const queueCombatValueBurst = (kind: 'damage' | 'heal', value: number, point: CombatPoint) => {
    const key = ++combatValueBurstKey
    combatValueBursts.value.push({
        key,
        kind,
        value,
        x: point.x,
        y: point.y,
    })

    const timeoutId = window.setTimeout(() => {
        combatValueBursts.value = combatValueBursts.value.filter((burst) => burst.key !== key)
        combatValueBurstTimeouts.delete(key)
    }, COMBAT_VALUE_BURST_DURATION_MS)

    combatValueBurstTimeouts.set(key, timeoutId)
}

const getHeroCenterForSide = (side: Side): CombatPoint | null => {
    const heroId = gameState.value.heroes[side]?.hero_id
    if (!heroId) {
        return null
    }

    return getEntityCenter(heroId)
}

const getSideFallbackPoint = (side: Side): CombatPoint | null => {
    const board = boardSurface.value
    if (!board) {
        return null
    }

    const boardRect = board.getBoundingClientRect()
    const isBottomSide = side === bottomSide.value

    return {
        x: boardRect.width * 0.5,
        y: boardRect.height * (isBottomSide ? 0.84 : 0.16)
    }
}

const getPlayedSpellCardPoint = (side: Side): CombatPoint | null => {
    const board = boardSurface.value
    if (!board) {
        return null
    }

    const boardRect = board.getBoundingClientRect()
    const isBottomSide = side === bottomSide.value

    return {
        x: boardRect.width * 0.5,
        y: isBottomSide
            ? boardRect.height - PLAYED_SPELL_CARD_CENTER_OFFSET_PX - PLAYED_SPELL_CARD_FLOAT_OFFSET_PX
            : PLAYED_SPELL_CARD_CENTER_OFFSET_PX + PLAYED_SPELL_CARD_FLOAT_OFFSET_PX
    }
}

const getPlayedSpellCardStyle = (side: Side): Record<string, string> => {
    const isBottomSide = side === bottomSide.value

    return {
        left: '50%',
        top: isBottomSide
            ? `calc(100% - ${PLAYED_SPELL_CARD_CENTER_OFFSET_PX}px)`
            : `${PLAYED_SPELL_CARD_CENTER_OFFSET_PX}px`
    }
}

const getSpellSourcePoint = (side: Side): CombatPoint | null => {
    return getPlayedSpellCardPoint(side) ?? getHeroCenterForSide(side) ?? getSideFallbackPoint(side)
}

const getSpellCardAnimationLingerMs = () => {
    const queuedAnimationCount = combatAnimationQueue.length + (activeCombatAnimation.value ? 1 : 0)
    const animationWaitMs = queuedAnimationCount * COMBAT_ANIMATION_DURATION_MS

    return animationWaitMs + COMBAT_ANIMATION_DURATION_MS + PLAYED_SPELL_CARD_AFTER_ANIMATION_MS
}

const queuePlayedSpellCard = (update: PlayCardUpdate) => {
    showPlayedSpellCard(update.card_id, update.side)
}

const queueCombatAnimation = (update: DamageUpdate) => {
    if (overlay.value) {
        return
    }

    syncEntityFrames()

    const target = getEntityCenter(update.target_id)
    if (!target) {
        return
    }

    queueCombatValueBurst('damage', update.damage, target)

    const isSpellDamage = isSpellDamageUpdate(update)
    if (isSpellDamage) {
        showPlayedSpellCard(update.source_id, update.side, getSpellCardAnimationLingerMs())
    }

    const source = isSpellDamage
        ? getSpellSourcePoint(update.side)
        : getEntityCenter(update.source_id)
    if (!source) {
        return
    }

    const distance = Math.hypot(target.x - source.x, target.y - source.y)
    if (distance < 16) {
        return
    }

    combatAnimationQueue.push({
        key: ++combatAnimationKey,
        kind: isSpellDamage ? 'spell-damage' : 'damage',
        sourceId: update.source_id,
        targetId: update.target_id,
        source,
        target,
        value: update.damage,
        isRetaliation: Boolean(update.is_retaliation)
    })

    playNextCombatAnimation()
}

const queueHealAnimation = (update: HealUpdate) => {
    if (overlay.value) {
        return
    }

    syncEntityFrames()

    const target = getEntityCenter(update.target_id)
    if (!target) {
        return
    }

    queueCombatValueBurst('heal', update.amount, target)

    const isSpellHeal = isSpellHealUpdate(update)
    if (isSpellHeal) {
        showPlayedSpellCard(update.source_id, update.side, getSpellCardAnimationLingerMs())
    }

    const source = isSpellHeal
        ? getSpellSourcePoint(update.side)
        : getEntityCenter(update.source_id)

    combatAnimationQueue.push({
        key: ++combatAnimationKey,
        kind: 'heal',
        sourceId: update.source_id,
        targetId: update.target_id,
        source: source ?? target,
        target,
        value: update.amount,
        isRetaliation: false
    })

    playNextCombatAnimation()
}

const getCombatVectorStyle = (entityId: string): Record<string, string> | undefined => {
    const animation = activeCombatAnimation.value
    if (!animation) {
        return undefined
    }

    let from: CombatPoint
    let to: CombatPoint
    let magnitude: number

    if (animation.kind === 'heal') {
        if (animation.sourceId !== animation.targetId && animation.sourceId === entityId) {
            from = animation.source
            to = animation.target
            magnitude = HEAL_ENTITY_DRIFT
        } else {
            return undefined
        }
    } else if (animation.kind === 'spell-damage') {
        if (animation.targetId === entityId) {
            from = animation.target
            to = animation.source
            magnitude = SPELL_ENTITY_PULSE
        } else {
            return undefined
        }
    } else if (animation.sourceId === entityId) {
        from = animation.source
        to = animation.target
        magnitude = COMBAT_ENTITY_LUNGE
    } else if (animation.targetId === entityId) {
        from = animation.target
        to = animation.source
        magnitude = COMBAT_ENTITY_RECOIL
    } else {
        return undefined
    }

    const dx = to.x - from.x
    const dy = to.y - from.y
    const distance = Math.hypot(dx, dy) || 1

    return {
        '--combat-offset-x': `${(dx / distance) * magnitude}px`,
        '--combat-offset-y': `${(dy / distance) * magnitude}px`,
    }
}

const getCombatEntityClass = (entityId: string) => {
    const animation = activeCombatAnimation.value
    if (!animation) {
        return ''
    }

    if (animation.kind === 'heal') {
        if (animation.targetId === entityId) {
            return 'combat-entity combat-entity--heal-target'
        }

        if (animation.sourceId === entityId && animation.sourceId !== animation.targetId) {
            return 'combat-entity combat-entity--heal-source'
        }

        return ''
    }

    if (animation.kind === 'spell-damage') {
        if (animation.targetId === entityId) {
            return 'combat-entity combat-entity--spell-target'
        }

        return ''
    }

    if (animation.sourceId === entityId) {
        return 'combat-entity combat-entity--source'
    }

    if (animation.targetId === entityId) {
        return 'combat-entity combat-entity--target'
    }

    return ''
}

const getCombatEntityStyle = (entityId: string) => {
    return getCombatVectorStyle(entityId)
}

// Helper methods from store
const get_card = (card_id: string | number) => {
    return gameStore.getCard(String(card_id))
}

const get_creature = (creature_id: string) => {
    return gameStore.getCreature(String(creature_id))
}

const getAttackUnavailableReason = (creature: Creature): string | null => {
    if (creature.exhausted) return 'Creature is exhausted'
    if (creature.attack <= 0) return 'Creature has no attack'
    return null
}

const getHero = (hero_id: string) => {
    return gameState.value.heroes[hero_id]
}

const isHandCardActive = (card_id: string | number) => {
    return gameStore.isHandCardActive(String(card_id))
}

const isMulliganCardSelected = (cardId: string) => {
    return mulliganSelectedCardIds.value.includes(cardId)
}

const toggleMulliganCard = (cardId: string) => {
    if (ownMulliganDone.value || mulliganSubmitting.value) return
    if (!mulliganCards.value.includes(cardId)) return

    if (isMulliganCardSelected(cardId)) {
        mulliganSelectedCardIds.value = mulliganSelectedCardIds.value.filter(
            selectedCardId => selectedCardId !== cardId
        )
        return
    }

    mulliganSelectedCardIds.value = [...mulliganSelectedCardIds.value, cardId]
}

const handleSubmitMulligan = async () => {
    if (ownMulliganDone.value || mulliganSubmitting.value) return
    if (isAutoSwitchingGame.value) return

    mulliganSubmitting.value = true
    const selectedCardIds = [...mulliganSelectedCardIds.value]
    const sent = await sendTurnPassingAction(() => {
        gameStore.submitMulligan(selectedCardIds)
    })

    if (!sent) {
        mulliganSubmitting.value = false
    }
}

/* Click Handlers - Opening Entity Details or Initiating Actions */

// When clicking a card in hand (always owned by player)
const handleClickHandCard = (card_id: string) => {
    const card = get_card(card_id)
    if (!card) return

    // If it's a spell that requires targeting, go directly to targeting
    if (card.card_type === 'spell' && requiresTarget(card)) {
        pendingPlay.value = { card_id, position: 0 }  // Set pendingPlay for spell casting
        targetingState.value = {
            sourceType: 'spell',
            sourceId: card_id,
            allowedTypes: convertAllowedTargets(getAllowedTargets(card)),
            scope: getSpellTargetScope(card),
            sourceCard: card,
            errorMessage: null,
            title: 'Cast Spell',
            bypassTaunt: true
        }
        overlay.value = 'select_target'
        overlayTitle.value = 'Select Target'
        return
    }

    // Otherwise show entity detail (for creatures or non-targeting spells)
    selectedEntity.value = { type: 'card', id: card_id, isOwned: true }
    overlay.value = 'entity_detail'
    overlayTitle.value = 'Card Details'
}

// When clicking own creature on board - show details if not your turn, otherwise go to targeting
const handleClickOwnCreature = (creature_id: string) => {
    console.log('handleClickOwnCreature', creature_id)
    const creature = get_creature(creature_id)
    if (!creature) return

    // If it's not the player's turn, just show entity details (no attacking)
    if (gameState.value.active !== bottomSide.value) {
        selectedEntity.value = { type: 'creature', id: creature_id, isOwned: true }
        overlay.value = 'entity_detail'
        overlayTitle.value = 'Your Creature'
        return
    }

    // It's the player's turn, allow targeting for attack
    targetingState.value = {
        sourceType: 'creature',
        sourceId: creature_id,
        allowedTypes: 'both',  // Creatures can attack both heroes and other creatures
        scope: 'enemy',
        sourceCard: creature,
        errorMessage: getAttackUnavailableReason(creature),
        title: 'Select Attack Target'
    }
    overlay.value = 'select_target'
    overlayTitle.value = 'Attack'
}

// When clicking opposing creature (just for info, cannot attack)
const handleClickOpposingCreature = (creature_id: string) => {
    console.log('handleClickOpposingCreature', creature_id)
    selectedEntity.value = { type: 'creature', id: creature_id, isOwned: false }
    overlay.value = 'entity_detail'
    overlayTitle.value = 'Enemy Creature'
}

// When clicking own hero
const handleClickOwnHero = () => {
    if (!ownHero.value || !viewer.value) return
    console.log('handleClickOwnHero', ownHero.value.hero_id)
    // Store the side (viewer) as the ID since heroes are keyed by side in the state
    selectedEntity.value = { type: 'hero', id: viewer.value, isOwned: true }
    overlay.value = 'entity_detail'
    overlayTitle.value = 'Hero Power'
}

// When clicking opposing hero (just for info, cannot use)
const handleClickOpposingHero = () => {
    if (!opposingHero.value || !viewer.value) return
    console.log('handleClickOpposingHero', opposingHero.value.hero_id)
    // Store the opposing side as the ID
    const opposingSide = viewer.value === 'side_a' ? 'side_b' : 'side_a'
    selectedEntity.value = { type: 'hero', id: opposingSide, isOwned: false }
    overlay.value = 'entity_detail'
    overlayTitle.value = `${opposingHero.value.player_name}` || 'Enemy Hero'
}

/* Action Handlers - From EntityDetail Component */

// Place creature card on board
const handlePlaceCreature = (card_id: string) => {
    console.log('handlePlaceCreature', card_id)
    const card = get_card(card_id)
    if (!card) return

    // If board is empty, automatically play at position 0
    if (!ownBoard.value || ownBoard.value.length === 0) {
        // Check if the card has a battlecry that needs a target
        if (requiresBattlecryTarget(card)) {
            const allowedTargets = getBattlecryAllowedTargets(card)
            const targetScope = getBattlecryTargetScope(card)
            pendingPlay.value = { card_id, position: 0 }
            targetingState.value = {
                sourceType: 'battlecry',
                sourceId: card_id,
                allowedTypes: convertAllowedTargets(allowedTargets),
                scope: targetScope,
                sourceCard: card,
                errorMessage: null,
                title: 'Choose Battlecry Target',
                bypassTaunt: getBattlecryBypassTaunt(card)
            }
            overlay.value = 'select_target'
            overlayTitle.value = 'Battlecry Target'
            return
        }

        // No battlecry target required, play immediately at position 0
        gameStore.playCard(card_id, 0)
        closeOverlay()
        return
    }

    // Board is not empty, show placement interface
    selectedCardId.value = card_id
    overlay.value = 'place_creature'
    overlayTitle.value = 'Place Creature'
}

// Cast spell card
const handleCastSpell = (card_id: string) => {
    console.log('handleCastSpell', card_id)
    const card = get_card(card_id)
    if (!card) return

    // If spell requires target, open target selector
    if (requiresTarget(card)) {
        pendingPlay.value = { card_id, position: 0 }
        targetingState.value = {
            sourceType: 'spell',
            sourceId: card_id,
            allowedTypes: convertAllowedTargets(getAllowedTargets(card)),
            scope: getSpellTargetScope(card),
            sourceCard: card,
            errorMessage: null,
            title: 'Cast Spell',
            bypassTaunt: true
        }
        overlay.value = 'select_target'
        overlayTitle.value = 'Select Target'
        return
    }

    // No target required, cast immediately
    gameStore.playCard(card_id, 0)
    closeOverlay()
}

// Creature attack
const handleAttack = (creature_id: string) => {
    console.log('handleAttack', creature_id)
    const creature = get_creature(creature_id)
    if (!creature) return

    targetingState.value = {
        sourceType: 'creature',
        sourceId: creature_id,
        allowedTypes: 'both',  // Creatures can attack both heroes and other creatures
        scope: 'enemy',
        sourceCard: creature,
        errorMessage: getAttackUnavailableReason(creature),
        title: 'Select Attack Target'
    }
    overlay.value = 'select_target'
    overlayTitle.value = 'Attack'
}

// Use hero power
const handleUseHero = (side_id: string) => {
    console.log('handleUseHero', side_id)
    const hero = getHero(side_id)
    if (!hero) return

    if (!heroPowerRequiresTarget(hero)) {
        gameStore.useHero(hero.hero_id)
        closeOverlay()
        return
    }

    // Check if hero power deals spell damage (bypasses taunt)
    let bypassTaunt = false
    if (hero.hero_power?.actions) {
        bypassTaunt = hero.hero_power.actions.some((action: any) =>
            action.action === 'damage' && action.damage_type === 'spell'
        )
    }

    targetingState.value = {
        sourceType: 'hero',
        sourceId: hero.hero_id,  // Use the actual hero_id for the backend command
        allowedTypes: 'both',  // Hero powers can target various things
        scope: getHeroPowerTargetScope(hero), // Determine scope based on hero power actions
        sourceCard: null,
        errorMessage: !canUseHero.value ? 'Cannot use hero power' : null,
        title: 'Use Hero Power',
        bypassTaunt: bypassTaunt
    }
    overlay.value = 'select_target'
    overlayTitle.value = 'Hero Power'
}

/* Placement and Targeting Callbacks */

// When placement position is selected from PlaceCreature
const onPlacementSelected = (payload: { card_id: string; position: number; allowedTargets: Array<'card' | 'hero' | 'any'>; targetScope: 'enemy' | 'friendly' }) => {
    console.log('onPlacementSelected', payload)

    // If battlecry requires target, open target selector
    pendingPlay.value = { card_id: payload.card_id, position: payload.position }

    const card = get_card(payload.card_id)
    targetingState.value = {
        sourceType: 'battlecry',
        sourceId: payload.card_id,
        allowedTypes: convertAllowedTargets(payload.allowedTargets),
        scope: payload.targetScope,
        sourceCard: card || null,
        errorMessage: null,
        title: 'Choose Battlecry Target',
        bypassTaunt: card ? getBattlecryBypassTaunt(card) : false
    }
    overlay.value = 'select_target'
    overlayTitle.value = 'Battlecry Target'
}

// When target is selected from Target component
const onTargetSelected = (target: { target_type: 'creature' | 'hero'; target_id: string }) => {
    console.log('onTargetSelected', target)
    if (!targetingState.value) return

    const { sourceType, sourceId } = targetingState.value

    // Handle battlecry targeting (card being played with battlecry)
    if (sourceType === 'battlecry' && pendingPlay.value) {
        const { card_id, position } = pendingPlay.value
        // Convert 'creature' to 'card' for backend compatibility
        const backendTarget = {
            target_type: target.target_type === 'creature' ? 'card' as const : target.target_type,
            target_id: target.target_id
        }
        gameStore.playCard(card_id, position, backendTarget)
        pendingPlay.value = null
        closeOverlay()
        return
    }

    // Handle spell targeting
    if (sourceType === 'spell' && pendingPlay.value) {
        const { card_id } = pendingPlay.value
        const backendTarget = {
            target_type: target.target_type === 'creature' ? 'card' as const : target.target_type,
            target_id: target.target_id
        }
        gameStore.playCard(card_id, 0, backendTarget)
        pendingPlay.value = null
        closeOverlay()
        return
    }

    // Handle creature attack
    if (sourceType === 'creature') {
        if (target.target_type === 'creature') {
            gameStore.useCardOnCard(sourceId, target.target_id)
        } else {
            gameStore.useCardOnHero(sourceId, target.target_id)
        }
        closeOverlay()
        return
    }

    // Handle hero power
    if (sourceType === 'hero') {
        if (target.target_type === 'creature') {
            gameStore.useHeroOnCard(sourceId, target.target_id)
        } else {
            gameStore.useHeroOnHero(sourceId, target.target_id)
        }
        closeOverlay()
        return
    }
}

/* Menu Handlers */

const handleEndTurn = async () => {
    if (gameOver.value.isGameOver) return

    await sendTurnPassingAction(() => {
        gameStore.endTurn()
    })
}

const sendTurnPassingAction = async (sendAction: () => void): Promise<boolean> => {
    if (isIntroGame.value) {
        clearAutoSwitch()
        activeGames.value = []
        sendAction()
        return true
    }

    if (isAutoSwitchingGame.value) return false

    autoSwitchLookupInFlight.value = true
    sendAction()

    const games = await fetchActiveGames()
    const availableNextGame = getNextGame(games)
    if (availableNextGame) {
        startAutoSwitchToGame(availableNextGame)
    } else {
        autoSwitchLookupInFlight.value = false
    }

    return true
}

const handleMenuClick = () => {
    overlay.value = 'menu'
    overlayTitle.value = "Menu"
    if (isIntroGame.value) {
        clearAutoSwitch()
        activeGames.value = []
        return
    }
    fetchActiveGames()
}

const handleClickUpdates = () => {
    overlay.value = 'updates'
    overlayTitle.value = "Game Log"
}

const handleClickHowToPlay = () => {
    overlay.value = 'how_to_play'
    overlayTitle.value = "How to Play"
}

const handleClickExtendTime = () => {
    gameStore.extendOpponentTime()
}

const handleClickDebug = () => {
    overlay.value = 'debug'
    overlayTitle.value = "Debug"
}

const fetchActiveGames = async (): Promise<ActiveGameSummary[]> => {
    const slug = titleStore.titleSlug ?? (route.params.slug as string | undefined)
    if (!slug) return activeGames.value

    try {
        const response = await axios.get(`/titles/${slug}/games/`)
        activeGames.value = (response.data.games || []).filter(
            (game: ActiveGameSummary) => game.type !== 'intro'
        )
    } catch (error) {
        console.error('Failed to fetch active games', error)
        activeGames.value = []
    }

    return activeGames.value
}

const clearAutoSwitchTimeouts = () => {
    if (autoSwitchNavigateTimeout !== null) {
        clearTimeout(autoSwitchNavigateTimeout)
        autoSwitchNavigateTimeout = null
    }
    if (autoSwitchClearTimeout !== null) {
        clearTimeout(autoSwitchClearTimeout)
        autoSwitchClearTimeout = null
    }
}

const clearAutoSwitch = () => {
    clearAutoSwitchTimeouts()
    autoSwitchLookupInFlight.value = false
    autoSwitchTarget.value = null
}

const startAutoSwitchToGame = (target: ActiveGameSummary) => {
    clearAutoSwitchTimeouts()
    autoSwitchLookupInFlight.value = false
    autoSwitchTarget.value = target

    autoSwitchNavigateTimeout = window.setTimeout(async () => {
        autoSwitchNavigateTimeout = null
        const slug = titleStore.titleSlug ?? (route.params.slug as string)
        gameStore.disconnectWebSocket()
        await router.push({
            name: 'Board',
            params: {
                slug,
                game_id: target.id,
            },
        })

        autoSwitchClearTimeout = window.setTimeout(() => {
            autoSwitchClearTimeout = null
            autoSwitchTarget.value = null
        }, AUTO_SWITCH_CLEAR_MS)
    }, AUTO_SWITCH_NAVIGATE_MS)
}

const handleRematch = async () => {
    if (rematchLoading.value) return
    rematchLoading.value = true
    const notificationStore = useNotificationStore()
    try {
        const response = await axios.post(
            `/gameplay/games/${gameId.value}/rematch/`,
            {},
            { headers: { Authorization: `Bearer ${authStore.accessToken}` } }
        )
        const titleSlug = response.data.title_slug
        notificationStore.success('Rematch challenge sent!')
        router.push({ name: 'Title', params: { slug: titleSlug } })
    } catch (error: any) {
        const message = error.response?.data?.error || 'Failed to send rematch challenge'
        notificationStore.error(message)
    } finally {
        rematchLoading.value = false
    }
}

const handleIntroSignup = () => {
    gameStore.disconnectWebSocket()
    router.push({
        name: 'Login',
        query: {
            signup: '1',
            redirect: '/play',
        },
    })
}

const handleIntroRetry = async () => {
    if (rematchLoading.value) return
    rematchLoading.value = true
    const notificationStore = useNotificationStore()

    try {
        const game = await startIntroScenario()
        showingGameOver.value = false
        gameStore.disconnectWebSocket()
        await router.replace({
            name: 'Board',
            params: {
                slug: game.title_slug,
                game_id: game.id,
            },
            query: {
                intro: '1',
            },
        })
    } catch (error) {
        console.error('Failed to restart intro game', error)
        notificationStore.error('Failed to restart the intro game')
    } finally {
        rematchLoading.value = false
    }
}

/* Utility Functions */

// Check if a creature card has a battlecry that requires targeting
function requiresBattlecryTarget(card: CardInPlay): boolean {
    const traits = card.traits || []
    const battlecry = traits.find((t: any) => t.type === 'battlecry')
    if (!battlecry) return false

    const actions = battlecry.actions || []
    for (const action of actions) {
        // Battlecry actions that require targeting (damage, heal)
        if (
            (action.action === 'damage' || action.action === 'heal' || action.action === 'remove' || action.action === 'buff') &&
            action.scope !== 'all'
        ) {
            if (action.action === 'buff' && action.target === 'hero') {
                continue
            }
            return true
        }
    }
    return false
}

// Get allowed target types for battlecry
function getBattlecryAllowedTargets(card: CardInPlay): Array<'card' | 'hero' | 'any'> {
    const allowed = new Set<'card' | 'hero' | 'any'>()
    const traits = card.traits || []
    const battlecry = traits.find((t: any) => t.type === 'battlecry')
    if (!battlecry) return ['any']

    for (const action of battlecry.actions || []) {
        if (action.action === 'damage') {
            if (action.target === 'creature' || action.target === 'enemy' || action.target === 'friendly') {
                allowed.add('card')
            }
            if (action.target === 'hero' || action.target === 'enemy' || action.target === 'friendly') {
                allowed.add('hero')
            }
        }
        if (action.action === 'heal') {
            if (action.target === 'creature' || action.target === 'friendly') {
                allowed.add('card')
            }
            if (action.target === 'hero' || action.target === 'friendly') {
                allowed.add('hero')
            }
        }
        if (action.action === 'remove') {
            // Remove targets enemy creatures only
            allowed.add('card')
        }
        if (action.action === 'buff') {
            if (action.target === 'creature' || action.target === 'friendly') {
                allowed.add('card')
            }
            if (action.target === 'hero' || action.target === 'friendly') {
                allowed.add('hero')
            }
        }
    }

    if (allowed.size === 0) allowed.add('any')
    return Array.from(allowed)
}

// Get target scope (enemy or friendly) for battlecry
function getBattlecryTargetScope(card: CardInPlay): 'enemy' | 'friendly' {
    const traits = card.traits || []
    const battlecry = traits.find((t: any) => t.type === 'battlecry')
    if (!battlecry) return 'enemy'

    for (const action of battlecry.actions || []) {
        // Heal actions target friendly units
        if (action.action === 'heal') {
            return 'friendly'
        }
        // Buff actions target friendly units
        if (action.action === 'buff') {
            return 'friendly'
        }
        if (action.action === 'damage') {
            if (action.target === 'friendly' || action.target === 'self') {
                return 'friendly'
            }
            return 'enemy'
        }
        // Remove actions target enemies
        if (action.action === 'remove') {
            return 'enemy'
        }
    }

    return 'enemy'
}

// Check if battlecry bypasses taunt (spell damage)
function getBattlecryBypassTaunt(card: CardInPlay): boolean {
    const traits = card.traits || []
    const battlecry = traits.find((t: any) => t.type === 'battlecry')
    if (!battlecry) return false

    return (battlecry.actions || []).some((action: any) =>
        action.action === 'damage' && action.damage_type === 'spell'
    )
}

// Close overlay and clear state
const closeOverlay = () => {
    overlay.value = null
    overlayTitle.value = ''
    targetingState.value = null
    selectedEntity.value = null
    selectedCardId.value = null
    pendingPlay.value = null
}

// Clear local UI state when game over is detected
const clearLocalState = () => {
    closeOverlay()
}

function requiresTarget(card: CardInPlay): boolean {
    const traits = card.traits || []

    // Check for spell with targeting
    if (card.card_type === 'spell') {
        for (const trait of traits) {
            const actions = trait.actions || []
            for (const action of actions) {
                // Actions that require targeting (single and cleave need targets, AOE doesn't)
                if ((action.action === 'damage' || action.action === 'heal' || action.action === 'remove' || action.action === 'buff') &&
                    action.scope !== 'all') {
                    if (action.action === 'buff' && action.target === 'hero') {
                        continue
                    }
                    return true
                }
            }
        }
    }

    return false
}

function getAllowedTargets(card: CardInPlay): Array<'card' | 'hero' | 'any'> {
    const allowed = new Set<'card' | 'hero' | 'any'>()
    const traits = card.traits || []

    for (const trait of traits) {
        const actions = trait.actions || []
        for (const action of actions) {
            if (action.action === 'damage') {
                if (action.target === 'creature' || action.target === 'enemy' || action.target === 'friendly') {
                    allowed.add('card')
                }
                if (action.target === 'hero' || action.target === 'enemy' || action.target === 'friendly') {
                    allowed.add('hero')
                }
            }
            if (action.action === 'heal') {
                // Heal targets friendlies (same side)
                // For now, map this to the same targeting system
                if (action.target === 'creature' || action.target === 'friendly') {
                    allowed.add('card')
                }
                if (action.target === 'hero' || action.target === 'friendly') {
                    allowed.add('hero')
                }
            }
            if (action.action === 'remove') {
                // Remove targets enemy creatures only
                allowed.add('card')
            }
            if (action.action === 'buff') {
                if (action.target === 'creature' || action.target === 'friendly') {
                    allowed.add('card')
                }
                if (action.target === 'hero' || action.target === 'friendly') {
                    allowed.add('hero')
                }
            }
        }
    }

    if (allowed.size === 0) allowed.add('any')
    return Array.from(allowed)
}

function getSpellTargetScope(card: CardInPlay): 'enemy' | 'friendly' {
    const traits = card.traits || []

    for (const trait of traits) {
        const actions = trait.actions || []
        for (const action of actions) {
            // Heal actions target friendly units
            if (action.action === 'heal') {
                return 'friendly'
            }
            // Buff actions target friendly units
            if (action.action === 'buff') {
                return 'friendly'
            }
            if (action.action === 'damage') {
                if (action.target === 'friendly' || action.target === 'self') {
                    return 'friendly'
                }
                return 'enemy'
            }
            // Remove actions target enemies
            if (action.action === 'remove') {
                return 'enemy'
            }
        }
    }

    return 'enemy'
}

function getHeroPowerTargetScope(hero: any): 'enemy' | 'friendly' {
    if (!hero.hero_power || !hero.hero_power.actions) {
        return 'enemy'
    }

    const actions = hero.hero_power.actions || []
    for (const action of actions) {
        // Heal actions target friendly units
        if (action.action === 'heal') {
            return 'friendly'
        }
        // Buff actions target friendly units
        if (action.action === 'buff') {
            return 'friendly'
        }
        if (action.action === 'damage') {
            if (action.target === 'friendly' || action.target === 'self') {
                return 'friendly'
            }
            return 'enemy'
        }
    }

    return 'enemy'
}

function heroPowerRequiresTarget(hero: any): boolean {
    if (!hero?.hero_power?.actions) {
        return false
    }

    return hero.hero_power.actions.some((action: any) => {
        if (action.action === 'buff' && action.target === 'hero') {
            return false
        }
        if (
            (action.action === 'damage' || action.action === 'heal' || action.action === 'remove' || action.action === 'buff') &&
            action.scope !== 'all' &&
            action.target !== 'self'
        ) {
            return true
        }
        return false
    })
}

// Convert old target format to new format
function convertAllowedTargets(targets: Array<'card' | 'hero' | 'any'>): 'creature' | 'hero' | 'both' {
    if (targets.includes('any')) return 'both'
    if (targets.includes('card') && targets.includes('hero')) return 'both'
    if (targets.includes('card')) return 'creature'
    if (targets.includes('hero')) return 'hero'
    return 'both'
}

/* Lifecycle and Watchers */

watch([title, gameId], async ([newTitle, newGameId], [, oldGameId]) => {
    if (!newTitle || !newGameId) {
        return
    }

    // Clear any open overlays when switching games in-place.
    if (oldGameId && oldGameId !== newGameId) {
        clearLocalState()
        showingGameOver.value = false
    }

    await gameStore.connectToGame(newGameId)
    if (isIntroGame.value) {
        clearAutoSwitch()
        activeGames.value = []
    } else {
        await fetchActiveGames()
    }
}, { immediate: true })

// Clear local state when game over is detected
watch(() => gameOver.value.isGameOver, (isGameOver) => {
    if (isGameOver) {
        clearLocalState()
        showingGameOver.value = true

        if (!isIntroGame.value && !gameState.value.elo_change) {
            gameStore.fetchEloChange(route.params.game_id as string)
        }
    }
})

watch(
    () => [
        isMulliganPhase.value,
        ownMulliganDone.value,
        mulliganCards.value.join(','),
    ],
    ([inMulligan, done]) => {
        if (!inMulligan) {
            mulliganSelectedCardIds.value = []
            mulliganSubmitting.value = false
            return
        }

        const eligibleCards = new Set(mulliganCards.value)
        mulliganSelectedCardIds.value = mulliganSelectedCardIds.value.filter(
            cardId => eligibleCards.has(cardId)
        )

        if (done) {
            mulliganSelectedCardIds.value = []
            mulliganSubmitting.value = false
        }
    },
    { immediate: true }
)

watch(() => overlay.value, (currentOverlay) => {
    if (currentOverlay) {
        resetCombatAnimations()
    }
})

watch(
    () => liveUpdateBatchId.value,
    (batchId, previousBatchId) => {
        if (batchId === previousBatchId) {
            return
        }

        for (const update of liveUpdateBatch.value) {
            if (isSpellPlayUpdate(update)) {
                queuePlayedSpellCard(update)
            }

            if (isCombatDamageUpdate(update) || (update?.type === 'update_damage' && isSpellDamageUpdate(update))) {
                queueCombatAnimation(update)
            } else if (isHealUpdate(update)) {
                queueHealAnimation(update)
            }
        }
    },
    { flush: 'sync' }
)

watch(
    () => [
        ownBoard.value.map((creature) => creature.creature_id).join(','),
        opposingBoard.value.map((creature) => creature.creature_id).join(','),
        ownHero.value?.hero_id ?? '',
        opposingHero.value?.hero_id ?? ''
    ],
    async () => {
        await nextTick()
        syncEntityFrames()
    },
    { flush: 'post' }
)

// Handle escape key to close overlay
const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === 'Escape' && overlay.value) {
        closeOverlay()
    }
}

// Update current time every second for countdown timer
let timeInterval: number | null = null

onMounted(() => {
    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('resize', syncEntityFrames)

    // Update current time every second for countdown timer
    timeInterval = window.setInterval(() => {
        currentTime.value = Date.now()
    }, 1000)

    nextTick(syncEntityFrames)
})

onUnmounted(() => {
    window.removeEventListener('keydown', handleKeyDown)
    window.removeEventListener('resize', syncEntityFrames)
    if (timeInterval !== null) {
        clearInterval(timeInterval)
    }
    clearAutoSwitch()
    resetCombatAnimations()
    gameStore.disconnect()
})
</script>

<style scoped>
.board {
    height: 100svh;
}

.next-game-transition {
    border-radius: 8px;
    animation: next-game-transition-in 760ms cubic-bezier(0.2, 0.78, 0.22, 1) both;
}

.next-game-progress {
    transform-origin: left;
    animation: next-game-progress 760ms linear both;
}

@keyframes next-game-transition-in {
    0% {
        opacity: 0;
        transform: translateY(10px) scale(0.98);
    }
    30% {
        opacity: 1;
    }
    100% {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}

@keyframes next-game-progress {
    from {
        transform: scaleX(0);
    }
    to {
        transform: scaleX(1);
    }
}

.combat-entity {
    will-change: transform, filter;
}

.combat-entity--source {
    animation: combat-entity-lunge 620ms cubic-bezier(0.2, 0.82, 0.32, 1);
}

.combat-entity--target {
    animation: combat-entity-hit 620ms cubic-bezier(0.2, 0.82, 0.32, 1);
}

.combat-entity--heal-source {
    animation: combat-entity-heal-source 620ms cubic-bezier(0.2, 0.82, 0.32, 1);
}

.combat-entity--heal-target {
    animation: combat-entity-heal-target 620ms cubic-bezier(0.2, 0.82, 0.32, 1);
}

.combat-entity--spell-target {
    animation: combat-entity-spell-target 620ms cubic-bezier(0.2, 0.82, 0.32, 1);
}

.played-spell-layer {
    perspective: 900px;
}

.played-spell-card {
    --played-spell-float-y: -12px;
    --played-spell-entry-y: 14px;
    --played-spell-exit-y: -24px;
    --played-spell-tilt: -3deg;
    position: absolute;
    width: 4.75rem;
    transform: translate(-50%, -50%);
    transform-origin: center;
    filter: drop-shadow(0 16px 22px rgba(0, 0, 0, 0.42));
    animation:
        played-spell-enter 280ms cubic-bezier(0.16, 0.84, 0.24, 1) both,
        played-spell-hover 1300ms ease-in-out 280ms infinite alternate;
    will-change: opacity, transform, filter;
}

.played-spell-card--top {
    --played-spell-float-y: 12px;
    --played-spell-entry-y: -14px;
    --played-spell-exit-y: 24px;
    --played-spell-tilt: 3deg;
}

.played-spell-card.is-leaving {
    animation: played-spell-exit 260ms cubic-bezier(0.4, 0, 0.2, 1) forwards;
}

.played-spell-card :deep(.game-card) {
    box-shadow:
        0 0 0 1px rgba(255, 255, 255, 0.18),
        0 0 24px rgba(96, 165, 250, 0.26);
}

@keyframes played-spell-enter {
    0% {
        opacity: 0;
        transform:
            translate(-50%, calc(-50% + var(--played-spell-entry-y)))
            rotate(var(--played-spell-tilt))
            scale(0.78);
        filter: drop-shadow(0 6px 10px rgba(0, 0, 0, 0.28));
    }

    100% {
        opacity: 1;
        transform:
            translate(-50%, calc(-50% + var(--played-spell-float-y)))
            rotate(0deg)
            scale(1);
        filter: drop-shadow(0 16px 22px rgba(0, 0, 0, 0.42));
    }
}

@keyframes played-spell-hover {
    0% {
        transform:
            translate(-50%, calc(-50% + var(--played-spell-float-y)))
            rotate(-1deg)
            scale(1);
    }

    100% {
        transform:
            translate(-50%, calc(-50% + var(--played-spell-float-y) - 5px))
            rotate(1deg)
            scale(1.02);
    }
}

@keyframes played-spell-exit {
    0% {
        opacity: 1;
        transform:
            translate(-50%, calc(-50% + var(--played-spell-float-y)))
            rotate(0deg)
            scale(1);
        filter: drop-shadow(0 16px 22px rgba(0, 0, 0, 0.42));
    }

    100% {
        opacity: 0;
        transform:
            translate(-50%, calc(-50% + var(--played-spell-exit-y)))
            rotate(var(--played-spell-tilt))
            scale(0.84);
        filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.22));
    }
}

@keyframes combat-entity-lunge {
    0%,
    100% {
        transform: translate3d(0, 0, 0) scale(1);
        filter: brightness(1);
    }

    28% {
        transform: translate3d(
            calc(var(--combat-offset-x, 0px) * 0.4),
            calc(var(--combat-offset-y, 0px) * 0.4),
            0
        ) scale(1.03);
        filter: brightness(1.1);
    }

    52% {
        transform: translate3d(var(--combat-offset-x, 0px), var(--combat-offset-y, 0px), 0) scale(1.05);
        filter: brightness(1.18);
    }
}

@keyframes combat-entity-hit {
    0%,
    36%,
    100% {
        transform: translate3d(0, 0, 0) scale(1);
        filter: brightness(1);
    }

    58% {
        transform: translate3d(var(--combat-offset-x, 0px), var(--combat-offset-y, 0px), 0) scale(0.97);
        filter: brightness(1.24);
    }

    74% {
        transform: translate3d(
            calc(var(--combat-offset-x, 0px) * -0.28),
            calc(var(--combat-offset-y, 0px) * -0.28),
            0
        ) scale(1.01);
    }
}

@keyframes combat-entity-heal-source {
    0%,
    100% {
        transform: translate3d(0, 0, 0) scale(1);
        filter: brightness(1) saturate(1);
    }

    30% {
        transform: translate3d(
            calc(var(--combat-offset-x, 0px) * 0.5),
            calc(var(--combat-offset-y, 0px) * 0.5),
            0
        ) scale(1.02);
        filter: brightness(1.08) saturate(1.1);
    }

    54% {
        transform: translate3d(var(--combat-offset-x, 0px), var(--combat-offset-y, 0px), 0) scale(1.03);
        filter: brightness(1.14) saturate(1.22);
    }
}

@keyframes combat-entity-heal-target {
    0%,
    100% {
        transform: translate3d(0, 0, 0) scale(1);
        filter: brightness(1) saturate(1);
    }

    32% {
        transform: translate3d(0, -2px, 0) scale(1.02);
        filter: brightness(1.08) saturate(1.12);
    }

    56% {
        transform: translate3d(0, -5px, 0) scale(1.05);
        filter: brightness(1.18) saturate(1.26);
    }

    78% {
        transform: translate3d(0, -2px, 0) scale(1.02);
    }
}

@keyframes combat-entity-spell-target {
    0%,
    100% {
        transform: translate3d(0, 0, 0) scale(1);
        filter: brightness(1) saturate(1);
    }

    42% {
        transform: translate3d(
            calc(var(--combat-offset-x, 0px) * 0.32),
            calc(var(--combat-offset-y, 0px) * 0.32),
            0
        ) scale(0.985);
        filter: brightness(1.12) saturate(1.16);
    }

    62% {
        transform: translate3d(0, 0, 0) scale(1.04);
        filter: brightness(1.22) saturate(1.24);
    }

    80% {
        transform: translate3d(0, 0, 0) scale(1.015);
    }
}
</style>
