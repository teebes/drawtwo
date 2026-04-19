<template>
    <div class="pointer-events-none absolute inset-0 z-40 overflow-hidden">
        <div
            v-for="burst in bursts"
            :key="burst.key"
            class="combat-burst"
            :class="burst.kind === 'heal' ? 'combat-burst--heal' : 'combat-burst--damage'"
            :style="{
                left: `${burst.x}px`,
                top: `${burst.y - 18}px`,
            }">
            <span>{{ burst.kind === 'heal' ? '+' : '-' }}{{ burst.value }}</span>
        </div>
    </div>
</template>

<script setup lang="ts">
interface CombatValueBurst {
    key: number
    kind: 'damage' | 'heal'
    value: number
    x: number
    y: number
}

defineProps<{
    bursts: CombatValueBurst[]
}>()
</script>

<style scoped>
.combat-burst {
    position: absolute;
    transform: translate(-50%, -50%);
    padding: 0.2rem 0.6rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.01em;
    animation: combat-burst-float 2200ms cubic-bezier(0.16, 0.84, 0.24, 1);
}

.combat-burst--damage {
    border: 1px solid rgba(251, 191, 36, 0.35);
    background: rgba(17, 24, 39, 0.88);
    color: rgba(255, 249, 237, 0.96);
    box-shadow:
        0 10px 26px rgba(15, 23, 42, 0.24),
        0 0 12px rgba(251, 191, 36, 0.16);
}

.combat-burst--heal {
    border: 1px solid rgba(167, 243, 208, 0.46);
    background: rgba(6, 78, 59, 0.82);
    color: rgba(236, 253, 245, 0.98);
    box-shadow:
        0 10px 24px rgba(6, 78, 59, 0.2),
        0 0 12px rgba(110, 231, 183, 0.14);
}

@keyframes combat-burst-float {
    0% {
        opacity: 0;
        transform: translate(-50%, 2px) scale(0.72);
    }

    10% {
        opacity: 1;
        transform: translate(-50%, -8px) scale(1);
    }

    74% {
        opacity: 1;
        transform: translate(-50%, -22px) scale(1.02);
    }

    100% {
        opacity: 0;
        transform: translate(-50%, -34px) scale(1.04);
    }
}
</style>
