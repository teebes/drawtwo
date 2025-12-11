<template>

    <!-- Damage -->
    <div class="game-update flex items-center" v-if="props.update.type === 'update_damage'">
        <UpdateEntity
            v-if="source && gameStore.viewer"
            :name="source.name"
            :art_url="'art_url' in source ? source.art_url : null"
            :class="isViewerTurn ? 'border-green-500' : 'border-red-500'"
        />
        <div class="flex items-center mx-2">
            <div class="bg-red-500 text-white font-bold px-3 py-1 rounded-lg shadow-md flex items-center gap-1.5">
                <span class="text-sm">⚔️</span>
                <span>{{ props.update.damage }}</span>
                <span class="text-xs">→</span>
            </div>
        </div>
        <UpdateEntity
            v-if="target && gameStore.viewer"
            :name="target.name"
            :art_url="'art_url' in target ? target.art_url : null"
            :class="isViewerTurn ? 'border-red-500' : 'border-green-500'"
        />
    </div>

    <!-- Heal -->
    <div class="game-update flex items-center" v-else-if="props.update.type === 'update_heal'">
        <UpdateEntity
            v-if="source && gameStore.viewer"
            :name="source.name"
            :art_url="'art_url' in source ? source.art_url : null"
            :class="isViewerTurn ? 'border-green-500' : 'border-red-500'"
        />
        <div class="flex items-center mx-2">
            <div class="bg-green-500 text-white font-bold px-3 py-1 rounded-lg shadow-md flex items-center gap-1.5">
                <span class="text-sm">💚</span>
                <span>{{ props.update.amount }}</span>
                <span class="text-xs">→</span>
            </div>
        </div>
        <UpdateEntity
            v-if="target && gameStore.viewer"
            :name="target.name"
            :art_url="'art_url' in target ? target.art_url : null"
            class="border-green-500"
            :class="isViewerTurn ? 'border-green-500' : 'border-red-500'"
        />
    </div>

    <!-- Draw -->
    <div class="game-update relative flex items-center" v-else-if="props.update.type === 'update_draw_card'">

        <template v-if="gameStore.viewer == props.update.side">
            <div class="mr-4">Draw</div>
            <UpdateEntity v-if="target"
                :name="target.name"
                :art_url="'art_url' in target ? target.art_url : null"
                class="border-green-500"/>
        </template>
        <template v-else>
            <UpdateEntity
                :name="opposing_hero.name"
                :art_url="'art_url' in opposing_hero ? opposing_hero.art_url : null"
                class="border-red-500" />
            <div class="ml-4">Draws a card</div>

        </template>
    </div>

    <!-- Play -->
    <div class="game-update relative flex items-center" v-else-if="props.update.type === 'update_play_card'">
        <div class="mr-4">Play</div>
        <UpdateEntity v-if="source && gameStore.viewer"
            :name="source.name"
            :art_url="'art_url' in source ? source.art_url : null"
            :class="isViewerTurn ? 'border-green-500' : 'border-red-500'"/>
        <!-- <span class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">⬇️</span> -->
    </div>

    <!-- Summon -->
    <div class="game-update flex items-center" v-else-if="props.update.type === 'update_summon'">
        <UpdateEntity
            v-if="source && gameStore.viewer"
            :name="source.name"
            :art_url="'art_url' in source ? source.art_url : null"
            :class="isViewerTurn ? 'border-green-500' : 'border-red-500'"
        />
        <div class="flex items-center mx-2">
            <div class="bg-purple-500 text-white font-bold px-3 py-1 rounded-lg shadow-md flex items-center gap-1.5">
                <span class="text-sm">✨</span>
                <span class="text-xs">→</span>
            </div>
        </div>
        <UpdateEntity
            v-if="target && gameStore.viewer"
            :name="target.name"
            :art_url="'art_url' in target ? target.art_url : null"
            :class="isViewerTurn ? 'border-green-500' : 'border-red-500'"
        />
    </div>

    <div class="game-update" v-else>
        {{ updateText(props.update) }}
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import UpdateEntity from './UpdateEntity.vue'
import { useGameStore } from '@/stores/game'
import { HeroInPlay } from '@/types/game'

interface Props {
    update: any
    hideSource?: boolean
}

const props = defineProps<Props>()

const gameStore = useGameStore()

const isViewerTurn = computed(() => {
    return gameStore.viewer === props.update.side
})

const updateText = (update: any) => {

    const hero: HeroInPlay = gameStore.gameState.heroes[update.side];
    const opposite_side = update.side === 'side_a' ? 'side_b' : 'side_a';
    const opposite_hero: HeroInPlay = gameStore.gameState.heroes[opposite_side];

    let side_name = hero.name + ': ';
    if (gameStore.viewer === update.side) {
        side_name = 'You: ';
    }

    if (props.hideSource) {
        side_name = '';
    }

    if (update.type === "update_draw_card") {
        const card = gameStore.getCard(update.card_id);
        const card_name = card?.name || 'a card';
        return `${side_name} Draw ${card_name}`;
    }

    if (update.type === "update_play_card") {
        const card = gameStore.getCard(update.card_id);
        const card_name = card?.name || 'a card';
        return `${side_name} Play ${card_name}`;
    }

    if (update.type === "update_end_turn") {
        return `${side_name} End Turn`;
    }

    if (update.type === "update_damage") {
        let source_name = '';
        if (update.source_type === "card" || update.source_type === "creature") {
            const card = update.source_type === "creature"
                ? gameStore.getCreature(update.source_id)
                : gameStore.getCard(update.source_id);
            source_name = card?.name || 'a unit';
        } else if (update.source_type === "hero") {
            if (update.source_id === hero.hero_id)
                source_name = hero.name;
            else
                source_name = opposite_hero.name;
        }

        let target_name = '';
        if (update.target_type === "card" || update.target_type === "creature") {
            const card = update.target_type === "creature"
                ? gameStore.getCreature(update.target_id)
                : gameStore.getCard(update.target_id);
            target_name = card?.name || 'a unit';
        } else if (update.target_type === "hero") {
            if (update.target_id === hero.hero_id)
                target_name = hero.name;
            else
                target_name = opposite_hero.name;
        }

        return `${side_name} ${source_name} > ${target_name} (-${update.damage})`;
    }

    if (update.type === "update_heal") {
        let source_name = '';
        if (update.source_type === "card" || update.source_type === "creature") {
            const card = update.source_type === "creature"
                ? gameStore.getCreature(update.source_id)
                : gameStore.getCard(update.source_id);
            source_name = card?.name || 'a unit';
        } else if (update.source_type === "hero") {
            if (update.source_id === hero.hero_id)
                source_name = hero.name;
            else
                source_name = opposite_hero.name;
        }

        let target_name = '';
        if (update.target_type === "card" || update.target_type === "creature") {
            const card = update.target_type === "creature"
                ? gameStore.getCreature(update.target_id)
                : gameStore.getCard(update.target_id);
            target_name = card?.name || 'a unit';
        } else if (update.target_type === "hero") {
            if (update.target_id === hero.hero_id)
                target_name = hero.name;
            else
                target_name = opposite_hero.name;
        }

        return `${side_name} ${source_name} > ${target_name} (+${update.amount})`;
    }

    if (update.type === "update_summon") {
        let source_name = '';
        if (update.source_type === "card") {
            const card = gameStore.getCard(update.source_id);
            source_name = card?.name || 'a card';
        }

        let target_name = '';
        if (update.target_type === "card") {
            const card = gameStore.getCard(update.target_id);
            target_name = card?.name || 'a card';
        }

        return `${side_name} ${source_name} summons ${target_name}`;
    }

    return `${update.side} - ${update.type}`
}

const source = computed(() => {
    if (props.update.source_type === "card") {
        return gameStore.getCard(props.update.source_id)
    } else if (props.update.source_type === "creature") {
        console.log('creature: ' + props.update.source_id)
        return gameStore.getCreature(props.update.source_id)
    } else if (props.update.source_type === "hero") {
        return gameStore.getHero(props.update.source_id)
    }
    return null
})

const target = computed(() => {
    if (props.update.target_type === "card") {
        return gameStore.getCard(props.update.target_id)
    } else if (props.update.target_type === "creature") {
        return gameStore.getCreature(props.update.target_id)
    } else if (props.update.target_type === "hero") {
        return gameStore.getHero(props.update.target_id)
    }
    return null
})

const opposing_hero = computed(() => {
    const opposite_side = gameStore.viewer === 'side_a' ? 'side_b' : 'side_a';
    const hero: HeroInPlay = gameStore.gameState.heroes[opposite_side]
    return hero;
})


</script>