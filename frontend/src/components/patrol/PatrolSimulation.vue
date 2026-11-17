<script setup lang="ts">
import { computed } from 'vue'
import type { PatrolRun } from '@sky/patrol'
const props = defineProps<{ run?: PatrolRun }>()
const progress = computed(() => {
  if (props.run?.status === 'completed') return 100
  if (props.run?.status !== 'running') return 0
  const fraction = props.run.processed / Math.max(1, props.run.imageCount)
  return props.run.stage === 'rendering' ? 60 + 38 * fraction : props.run.stage === 'evaluating' ? 10 + 48 * fraction : 5
})
const drone = computed(() => ({ x: 65 + progress.value * 6.5, y: 110 + Math.sin(progress.value / 16) * 25 }))
</script>
<template><section class="simulation"><div class="sim-heading"><strong>无人机水域巡逻 · 示意动画</strong><span>随后台评测阶段推进 · {{ progress.toFixed(0) }}%</span></div><svg viewBox="0 0 800 220" role="img" aria-label="无人机仿真巡逻示意，不是真实地理位置"><rect width="800" height="220" fill="#102b34" /><path d="M-20 110 C120 45 210 180 365 110 S620 145 830 70" stroke="#125f83" stroke-width="108" fill="none"/><path d="M65 110 C200 45 270 180 430 110 S620 145 715 95" stroke="#55c9e9" stroke-width="2" stroke-dasharray="7 9" fill="none" opacity=".7"/><g v-for="n in 13" :key="n" :transform="`translate(${n * 57}, ${n % 2 ? 12 : 185})`"><rect width="28" height="18" fill="#365364"/><rect x="31" y="4" width="18" height="14" fill="#274858"/></g><g :transform="`translate(${drone.x}, ${drone.y})`" class="drone"><circle r="26" fill="#5ce7ff" opacity=".13"/><path d="M-12 -12 L12 12 M-12 12 L12 -12" stroke="#e7fbff" stroke-width="4"/><circle v-for="(point,i) in [[-13,-13],[13,-13],[-13,13],[13,13]]" :key="i" :cx="point[0]" :cy="point[1]" r="7" fill="#0a2538" stroke="#6ceaff" stroke-width="2"/><rect x="-5" y="-8" width="10" height="16" rx="3" fill="#e7fbff"/></g><text x="18" y="210" fill="#afd4e4" font-size="11">视觉示意不修改Java飞行任务；影像来自HAIDA港区数据，与动画位置无对应关系。</text></svg></section></template>
<style scoped>.simulation { border:1px solid #24465d; background:#0b2132; overflow:hidden; }.sim-heading { display:flex; justify-content:space-between; gap:12px; padding:15px 20px; }.sim-heading strong { font-size:14px; }.sim-heading span { color:#85bacf; font-size:12px; }.simulation svg { display:block; width:100%; max-height:240px; }.drone { transition:transform 1s linear; }</style>
