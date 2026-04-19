<template>
    <div class="combat-layer pointer-events-none absolute inset-0 z-30 overflow-hidden">
        <template v-if="isHeal">
            <div class="heal-origin-flash" :style="originStyle"></div>
            <div v-if="hasTravel" class="heal-line" :style="trailStyle">
                <div class="heal-line-core"></div>
            </div>
            <div v-if="hasTravel" class="heal-orb" :style="boltStyle"></div>
            <div class="heal-impact" :style="impactStyle"></div>
        </template>
        <template v-else-if="isSpellDamage">
            <div class="spell-origin-flash" :style="originStyle"></div>
            <div class="spell-line" :style="trailStyle">
                <div class="spell-line-core"></div>
            </div>
            <div class="spell-bolt" :style="boltStyle"></div>
            <div class="spell-impact" :style="impactStyle"></div>
        </template>
        <template v-else>
            <div class="combat-origin-flash" :class="variantClass" :style="originStyle"></div>
            <div class="combat-line" :style="trailStyle">
                <div class="combat-line-core" :class="variantClass"></div>
            </div>
            <div class="combat-bolt" :class="variantClass" :style="boltStyle"></div>
            <div class="combat-impact" :class="variantClass" :style="impactStyle"></div>
        </template>
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
    kind: 'damage' | 'heal' | 'spell-damage'
    sourceId: string
    targetId: string
    source: CombatPoint
    target: CombatPoint
    isRetaliation: boolean
}

const props = defineProps<{
    animation: CombatAnimationState
}>()

const dx = computed(() => props.animation.target.x - props.animation.source.x)
const dy = computed(() => props.animation.target.y - props.animation.source.y)
const distance = computed(() => Math.hypot(dx.value, dy.value))
const angle = computed(() => `${Math.atan2(dy.value, dx.value)}rad`)
const isHeal = computed(() => props.animation.kind === 'heal')
const isSpellDamage = computed(() => props.animation.kind === 'spell-damage')
const hasTravel = computed(() => distance.value >= 16 && props.animation.sourceId !== props.animation.targetId)
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
</script>

<style scoped>
.combat-origin-flash,
.combat-line,
.combat-bolt,
.combat-impact,
.spell-origin-flash,
.spell-line,
.spell-bolt,
.spell-impact,
.heal-origin-flash,
.heal-line,
.heal-orb,
.heal-impact {
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

.heal-origin-flash {
    width: 30px;
    height: 30px;
    border-radius: 9999px;
    background: radial-gradient(
        circle,
        rgba(243, 255, 244, 0.98) 0%,
        rgba(74, 222, 128, 0.58) 38%,
        rgba(16, 185, 129, 0) 78%
    );
    filter: blur(1px);
    animation: heal-origin-flash 620ms cubic-bezier(0.2, 0.82, 0.32, 1);
}

.heal-line {
    height: 4px;
    transform: translateY(-50%) rotate(var(--attack-angle));
    transform-origin: left center;
    animation: heal-line 620ms cubic-bezier(0.2, 0.82, 0.32, 1);
}

.heal-line-core {
    width: 100%;
    height: 100%;
    border-radius: 9999px;
    background: linear-gradient(
        90deg,
        rgba(74, 222, 128, 0) 0%,
        rgba(74, 222, 128, 0.26) 18%,
        rgba(236, 253, 245, 0.9) 56%,
        rgba(45, 212, 191, 0.72) 100%
    );
    box-shadow:
        0 0 12px rgba(74, 222, 128, 0.22),
        0 0 22px rgba(45, 212, 191, 0.16);
}

.heal-orb {
    width: 18px;
    height: 18px;
    border-radius: 9999px;
    background: radial-gradient(
        circle,
        rgba(255, 255, 255, 0.98) 0%,
        rgba(167, 243, 208, 0.9) 38%,
        rgba(52, 211, 153, 0.64) 72%,
        rgba(52, 211, 153, 0) 100%
    );
    box-shadow:
        0 0 12px rgba(236, 253, 245, 0.38),
        0 0 24px rgba(52, 211, 153, 0.28);
    animation: heal-orb 620ms cubic-bezier(0.18, 0.88, 0.28, 1);
}

.heal-impact {
    width: 66px;
    height: 66px;
    border-radius: 9999px;
    border: 2px solid rgba(209, 250, 229, 0.66);
    background:
        radial-gradient(circle, rgba(236, 253, 245, 0.92) 0%, rgba(74, 222, 128, 0.22) 34%, rgba(74, 222, 128, 0) 72%),
        radial-gradient(circle, rgba(125, 211, 252, 0.2) 10%, rgba(125, 211, 252, 0) 64%);
    box-shadow:
        0 0 24px rgba(74, 222, 128, 0.14),
        0 0 42px rgba(45, 212, 191, 0.1);
    animation: heal-impact 620ms cubic-bezier(0.2, 0.82, 0.32, 1);
}

.spell-origin-flash {
    width: 34px;
    height: 34px;
    border-radius: 9999px;
    background: radial-gradient(
        circle,
        rgba(244, 247, 255, 0.98) 0%,
        rgba(129, 140, 248, 0.6) 34%,
        rgba(56, 189, 248, 0.24) 58%,
        rgba(56, 189, 248, 0) 82%
    );
    filter: blur(1px);
    animation: spell-origin-flash 620ms cubic-bezier(0.2, 0.82, 0.32, 1);
}

.spell-line {
    height: 4px;
    transform: translateY(-50%) rotate(var(--attack-angle));
    transform-origin: left center;
    animation: spell-line 620ms cubic-bezier(0.2, 0.82, 0.32, 1);
}

.spell-line-core {
    width: 100%;
    height: 100%;
    border-radius: 9999px;
    background: linear-gradient(
        90deg,
        rgba(129, 140, 248, 0) 0%,
        rgba(129, 140, 248, 0.3) 18%,
        rgba(244, 247, 255, 0.94) 52%,
        rgba(34, 211, 238, 0.76) 100%
    );
    box-shadow:
        0 0 12px rgba(129, 140, 248, 0.28),
        0 0 24px rgba(34, 211, 238, 0.18);
}

.spell-bolt {
    width: 20px;
    height: 20px;
    border-radius: 9999px;
    background:
        radial-gradient(circle, rgba(255, 255, 255, 0.98) 0%, rgba(191, 219, 254, 0.9) 34%, rgba(99, 102, 241, 0.66) 68%, rgba(99, 102, 241, 0) 100%);
    box-shadow:
        0 0 14px rgba(255, 255, 255, 0.32),
        0 0 28px rgba(99, 102, 241, 0.3);
    animation: spell-bolt 620ms cubic-bezier(0.14, 0.9, 0.26, 1);
}

.spell-impact {
    width: 72px;
    height: 72px;
    border-radius: 9999px;
    border: 2px solid rgba(191, 219, 254, 0.74);
    background:
        radial-gradient(circle, rgba(244, 247, 255, 0.92) 0%, rgba(96, 165, 250, 0.24) 30%, rgba(96, 165, 250, 0) 68%),
        radial-gradient(circle, rgba(129, 140, 248, 0.18) 10%, rgba(129, 140, 248, 0) 62%);
    box-shadow:
        0 0 28px rgba(96, 165, 250, 0.16),
        0 0 44px rgba(129, 140, 248, 0.12);
    animation: spell-impact 620ms cubic-bezier(0.2, 0.82, 0.32, 1);
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

@keyframes heal-origin-flash {
    0% {
        opacity: 0;
        transform: translate(-50%, -50%) scale(0.4);
    }

    20% {
        opacity: 0.98;
        transform: translate(-50%, -50%) scale(1);
    }

    100% {
        opacity: 0;
        transform: translate(-50%, -50%) scale(1.4);
    }
}

@keyframes spell-origin-flash {
    0% {
        opacity: 0;
        transform: translate(-50%, -50%) scale(0.34);
    }

    16% {
        opacity: 1;
        transform: translate(-50%, -50%) scale(1);
    }

    100% {
        opacity: 0;
        transform: translate(-50%, -50%) scale(1.46);
    }
}

@keyframes heal-line {
    0% {
        opacity: 0;
        transform: translateY(-50%) rotate(var(--attack-angle)) scaleX(0.12);
    }

    16% {
        opacity: 0.88;
    }

    100% {
        opacity: 0;
        transform: translateY(-50%) rotate(var(--attack-angle)) scaleX(1);
    }
}

@keyframes spell-line {
    0% {
        opacity: 0;
        transform: translateY(-50%) rotate(var(--attack-angle)) scaleX(0.1);
    }

    14% {
        opacity: 0.92;
    }

    100% {
        opacity: 0;
        transform: translateY(-50%) rotate(var(--attack-angle)) scaleX(1);
    }
}

@keyframes heal-orb {
    0% {
        opacity: 0;
        transform: translate(-50%, -50%) rotate(var(--attack-angle)) translateX(0) scale(0.55);
    }

    18% {
        opacity: 1;
    }

    100% {
        opacity: 0;
        transform: translate(-50%, -50%) rotate(var(--attack-angle)) translateX(var(--travel-distance)) scale(1.08);
    }
}

@keyframes spell-bolt {
    0% {
        opacity: 0;
        transform: translate(-50%, -50%) rotate(var(--attack-angle)) translateX(0) scale(0.48);
    }

    18% {
        opacity: 1;
    }

    100% {
        opacity: 0;
        transform: translate(-50%, -50%) rotate(var(--attack-angle)) translateX(var(--travel-distance)) scale(1.12);
    }
}

@keyframes heal-impact {
    0%,
    24% {
        opacity: 0;
        transform: translate(-50%, -50%) scale(0.22);
    }

    52% {
        opacity: 0.96;
        transform: translate(-50%, -50%) scale(0.9);
    }

    100% {
        opacity: 0;
        transform: translate(-50%, -50%) scale(1.28);
    }
}

@keyframes spell-impact {
    0%,
    24% {
        opacity: 0;
        transform: translate(-50%, -50%) scale(0.2);
    }

    52% {
        opacity: 0.98;
        transform: translate(-50%, -50%) scale(0.94);
    }

    100% {
        opacity: 0;
        transform: translate(-50%, -50%) scale(1.34);
    }
}

</style>
