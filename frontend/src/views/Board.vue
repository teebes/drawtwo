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
            @rematch="handleRematch" />

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
                    <div class="w-24 flex flex-col justify-center items-center text-center border-l border-gray-700 relative">
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
                        <span class="inline-block cursor-pointer" @click="handleMenuClick">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-label="Menu" xmlns="http://www.w3.org/2000/svg">
                                <rect y="5" width="24" height="2" rx="1" fill="currentColor"/>
                                <rect y="11" width="24" height="2" rx="1" fill="currentColor"/>
                                <rect y="17" width="24" height="2" rx="1" fill="currentColor"/>
                            </svg>
                        </span>
                    </div>
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
                    <span v-if="gameState.time_per_turn && gameState.time_per_turn > 0" class="text-gray-500 ml-2">
                        [ {{ timeLeftString }} ]
                    </span>
                    <span v-else class="text-gray-500 ml-2">[ {{ gameState.phase }} ]</span>
                </div>
                <GameButton
                    v-if="gameState.winner === 'none' && gameState.active === bottomSide"
                    variant="secondary"
                    class="m-2"
                    :class="{ 'ring-2 ring-primary-500': hasNoAvailableActions }"
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

            <CombatAnimationLayer
                v-if="activeCombatAnimation"
                :key="activeCombatAnimation.key"
                :animation="activeCombatAnimation" />
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
                @click-updates="handleClickUpdates"
                @click-extend-time="handleClickExtendTime"
                @click-debug="handleClickDebug"
            />

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
type OverlayType = 'entity_detail' | 'place_creature' | 'select_target' | 'menu' | 'updates' | 'debug' | null

// Local UI state
const overlay = ref<OverlayType>(null)
const overlayTitle = ref<string>('')

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

const showingGameOver = ref(false)
const rematchLoading = ref(false)
const boardSurface = ref<HTMLElement | null>(null)
const activeCombatAnimation = ref<CombatAnimationState | null>(null)
const combatValueBursts = ref<CombatValueBurst[]>([])

const combatAnimationQueue: CombatAnimationState[] = []
const entityElements = new Map<string, HTMLElement>()
const entityFrames = new Map<string, DOMRect>()
const combatValueBurstTimeouts = new Map<number, number>()

let combatAnimationKey = 0
let combatAnimationTimeout: number | null = null
let combatValueBurstKey = 0

const COMBAT_ENTITY_LUNGE = 14
const COMBAT_ENTITY_RECOIL = 10
const HEAL_ENTITY_DRIFT = 6
const SPELL_ENTITY_PULSE = 8
const COMBAT_ANIMATION_DURATION_MS = 620
const COMBAT_VALUE_BURST_DURATION_MS = 2200

const title = computed(() => titleStore.currentTitle)

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
        // If timer hasn't started yet (turn_expires is null), show phase as fallback
        return gameState.value.phase
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

const resetCombatAnimations = () => {
    clearCombatAnimationTimeout()
    activeCombatAnimation.value = null
    combatAnimationQueue.length = 0
    clearCombatValueBurstTimeouts()
    combatValueBursts.value = []
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

const getSpellSourcePoint = (side: Side): CombatPoint | null => {
    return getHeroCenterForSide(side) ?? getSideFallbackPoint(side)
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

    const source = getEntityCenter(update.source_id) ?? target

    combatAnimationQueue.push({
        key: ++combatAnimationKey,
        kind: 'heal',
        sourceId: update.source_id,
        targetId: update.target_id,
        source,
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
            title: 'Cast Spell'
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
            title: 'Cast Spell'
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
        gameStore.useHeroOnHero(hero.hero_id, hero.hero_id)
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

const handleEndTurn = () => {
    if (gameOver.value.isGameOver) return
    gameStore.endTurn()
}

const handleMenuClick = () => {
    overlay.value = 'menu'
    overlayTitle.value = "Menu"
}

const handleClickUpdates = () => {
    overlay.value = 'updates'
    overlayTitle.value = "Game Updates"
}

const handleClickExtendTime = () => {
    gameStore.extendOpponentTime()
}

const handleClickDebug = () => {
    overlay.value = 'debug'
    overlayTitle.value = "Debug"
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
            if (action.target === 'creature' || action.target === 'enemy') {
                allowed.add('card')
            }
            if (action.target === 'hero' || action.target === 'enemy') {
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
        // Damage actions target enemies
        if (action.action === 'damage') {
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
                if (action.target === 'creature' || action.target === 'enemy') {
                    allowed.add('card')
                }
                if (action.target === 'hero' || action.target === 'enemy') {
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
            // Damage actions target enemies
            if (action.action === 'damage') {
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
        // Damage actions target enemies
        if (action.action === 'damage') {
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
}, { immediate: true })

// Clear local state when game over is detected
watch(() => gameOver.value.isGameOver, (isGameOver) => {
    if (isGameOver) {
        clearLocalState()
        showingGameOver.value = true

        if (!gameState.value.elo_change) {
            gameStore.fetchEloChange(route.params.game_id as string)
        }
    }
})

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
    resetCombatAnimations()
    gameStore.disconnect()
})
</script>

<style scoped>
.board {
    height: 100svh;
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
