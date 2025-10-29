<template>
    <div class="game-update">{{ updateText(props.update) }}</div>
</template>

<script setup lang="ts">
import { useGameStore } from '@/stores/game'
import { HeroInPlay } from '@/types/game'

interface Props {
    update: any
}

const props = defineProps<Props>()

const gameStore = useGameStore()

const updateText = (update: any) => {

    const hero: HeroInPlay = gameStore.gameState.heroes[update.side];
    const opposite_side = update.side === 'side_a' ? 'side_b' : 'side_a';
    const opposite_hero: HeroInPlay = gameStore.gameState.heroes[opposite_side];

    let side_name = hero.name + ': ';
    if (gameStore.viewer === update.side) {
        side_name = 'You: ';
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


    return `${update.side} - ${update.type}`
}
</script>