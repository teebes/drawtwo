<template>
    <div class="combat-layer pointer-events-none absolute inset-0 z-30 overflow-hidden">
        <div class="combat-origin-flash" :class="variantClass" :style="originStyle"></div>
        <div class="combat-line" :style="trailStyle">
            <div class="combat-line-core" :class="variantClass"></div>
        </div>
        <div class="combat-bolt" :class="variantClass" :style="boltStyle"></div>
        <div class="combat-impact" :class="variantClass" :style="impactStyle"></div>
        <div class="combat-damage" :style="damageStyle">
            -{{ animation.damage }}
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface CombatPoint {
    x: number
    y: number
}

interface CombatAnimationState {
    key: number
    sourceId: string
    targetId: string
    source: CombatPoint
    target: CombatPoint
    damage: number
    isRetaliation: boolean
}

const props = defineProps<{
    animation: CombatAnimationState
}>()

const dx = computed(() => props.animation.target.x - props.animation.source.x)
const dy = computed(() => props.animation.target.y - props.animation.source.y)
const distance = computed(() => Math.hypot(dx.value, dy.value))
const angle = computed(() => `${Math.atan2(dy.value, dx.value)}rad`)
const variantClass = computed(() => props.animation.isRetaliation ? 'is-retaliation' : '')

const originStyle = computed(() => ({
    left: `${props.animation.source.x}px`,
    top: `${props.animation.source.y}px`,
}))

const trailStyle = computed(() => ({
    left: `${props.animation.source.x}px`,
    top: `${props.animation.source.y}px`,
    width: `${distance.value}px`,
    '--attack-angle': angle.value,
}))

const boltStyle = computed(() => ({
    left: `${props.animation.source.x}px`,
    top: `${props.animation.source.y}px`,
    '--attack-angle': angle.value,
    '--travel-distance': `${distance.value}px`,
}))

const impactStyle = computed(() => ({
    left: `${props.animation.target.x}px`,
    top: `${props.animation.target.y}px`,
}))

const damageStyle = computed(() => ({
    left: `${props.animation.target.x}px`,
    top: `${props.animation.target.y - 18}px`,
}))
</script>

<style scoped>
.combat-origin-flash,
.combat-line,
.combat-bolt,
.combat-impact,
.combat-damage {
    position: absolute;
    transform: translate(-50%, -50%);
}

.combat-origin-flash {
    width: 28px;
    height: 28px;
    border-radius: 9999px;
    background: radial-gradient(
        circle,
        rgba(255, 250, 230, 0.96) 0%,
        rgba(251, 191, 36, 0.65) 38%,
        rgba(248, 113, 24, 0) 76%
    );
    filter: blur(1px);
    animation: combat-origin-flash 620ms cubic-bezier(0.2, 0.82, 0.32, 1);
}

.combat-line {
    height: 3px;
    transform: translateY(-50%) rotate(var(--attack-angle));
    transform-origin: left center;
    animation: combat-line 620ms cubic-bezier(0.2, 0.82, 0.32, 1);
}

.combat-line-core {
    width: 100%;
    height: 100%;
    border-radius: 9999px;
    background: linear-gradient(
        90deg,
        rgba(251, 191, 36, 0) 0%,
        rgba(251, 191, 36, 0.38) 22%,
        rgba(255, 255, 255, 0.92) 58%,
        rgba(248, 113, 113, 0.78) 100%
    );
    box-shadow:
        0 0 10px rgba(251, 191, 36, 0.3),
        0 0 18px rgba(248, 113, 113, 0.22);
}

.combat-bolt {
    width: 26px;
    height: 10px;
    border-radius: 9999px;
    background: linear-gradient(90deg, rgba(255, 255, 255, 0.94), rgba(248, 113, 24, 0.94));
    box-shadow:
        0 0 12px rgba(255, 255, 255, 0.36),
        0 0 22px rgba(248, 113, 24, 0.34);
    animation: combat-bolt 620ms cubic-bezier(0.18, 0.88, 0.28, 1);
}

.combat-impact {
    width: 56px;
    height: 56px;
    border-radius: 9999px;
    border: 2px solid rgba(255, 248, 220, 0.72);
    background: radial-gradient(
        circle,
        rgba(255, 255, 255, 0.82) 0%,
        rgba(248, 113, 113, 0.26) 34%,
        rgba(248, 113, 113, 0) 72%
    );
    box-shadow: 0 0 28px rgba(248, 113, 113, 0.18);
    animation: combat-impact 620ms cubic-bezier(0.2, 0.82, 0.32, 1);
}

.combat-damage {
    padding: 0.2rem 0.55rem;
    border: 1px solid rgba(251, 191, 36, 0.35);
    border-radius: 9999px;
    background: rgba(17, 24, 39, 0.84);
    color: rgba(255, 249, 237, 0.96);
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.01em;
    box-shadow:
        0 10px 26px rgba(15, 23, 42, 0.24),
        0 0 12px rgba(251, 191, 36, 0.16);
    animation: combat-damage 620ms cubic-bezier(0.2, 0.82, 0.32, 1);
}

.is-retaliation.combat-origin-flash {
    background: radial-gradient(
        circle,
        rgba(255, 243, 243, 0.94) 0%,
        rgba(248, 113, 113, 0.64) 38%,
        rgba(244, 63, 94, 0) 76%
    );
}

.is-retaliation.combat-line-core {
    background: linear-gradient(
        90deg,
        rgba(248, 113, 113, 0) 0%,
        rgba(248, 113, 113, 0.34) 22%,
        rgba(255, 255, 255, 0.92) 56%,
        rgba(251, 146, 60, 0.74) 100%
    );
    box-shadow:
        0 0 10px rgba(248, 113, 113, 0.3),
        0 0 18px rgba(251, 146, 60, 0.2);
}

.is-retaliation.combat-bolt {
    background: linear-gradient(90deg, rgba(255, 255, 255, 0.92), rgba(248, 113, 113, 0.92));
    box-shadow:
        0 0 12px rgba(255, 255, 255, 0.3),
        0 0 22px rgba(248, 113, 113, 0.28);
}

.is-retaliation.combat-impact {
    border-color: rgba(255, 228, 230, 0.72);
    background: radial-gradient(
        circle,
        rgba(255, 255, 255, 0.8) 0%,
        rgba(248, 113, 113, 0.28) 34%,
        rgba(248, 113, 113, 0) 72%
    );
}

@keyframes combat-origin-flash {
    0% {
        opacity: 0;
        transform: translate(-50%, -50%) scale(0.3);
    }

    18% {
        opacity: 0.96;
        transform: translate(-50%, -50%) scale(1);
    }

    100% {
        opacity: 0;
        transform: translate(-50%, -50%) scale(1.35);
    }
}

@keyframes combat-line {
    0% {
        opacity: 0;
        transform: translateY(-50%) rotate(var(--attack-angle)) scaleX(0.18);
    }

    18% {
        opacity: 0.92;
    }

    100% {
        opacity: 0;
        transform: translateY(-50%) rotate(var(--attack-angle)) scaleX(1);
    }
}

@keyframes combat-bolt {
    0% {
        opacity: 0;
        transform: translate(-50%, -50%) rotate(var(--attack-angle)) translateX(0) scale(0.65);
    }

    16% {
        opacity: 1;
    }

    84% {
        opacity: 0.9;
    }

    100% {
        opacity: 0;
        transform: translate(-50%, -50%) rotate(var(--attack-angle)) translateX(var(--travel-distance)) scale(1.06);
    }
}

@keyframes combat-impact {
    0%,
    42% {
        opacity: 0;
        transform: translate(-50%, -50%) scale(0.18);
    }

    58% {
        opacity: 0.98;
        transform: translate(-50%, -50%) scale(0.78);
    }

    100% {
        opacity: 0;
        transform: translate(-50%, -50%) scale(1.22);
    }
}

@keyframes combat-damage {
    0%,
    44% {
        opacity: 0;
        transform: translate(-50%, 0) scale(0.76);
    }

    60% {
        opacity: 1;
        transform: translate(-50%, -8px) scale(1);
    }

    100% {
        opacity: 0;
        transform: translate(-50%, -24px) scale(1.04);
    }
}
</style>
