<script setup lang="ts">
import { computed } from 'vue'
import type { ChartDatum } from '../../utils/overviewMetrics'
const props = defineProps<{ items: ChartDatum[]; vertical?: boolean }>()
const max = computed(() => Math.max(1,...props.items.map(i => i.value)))
const rows = computed(() => props.items.map(i => ({ ...i, percentage: i.value / max.value * 100 })))
</script>
<template>
  <div class="bars" :class="{ vertical }" role="list">
    <div v-for="item in rows" :key="item.key" class="bar-item" role="listitem" :aria-label="`${item.label} ${item.value}`">
      <span class="bar-label">{{ item.label }}</span>
      <div class="bar-track"><div class="bar-fill" :style="{ '--bar-color':item.color, [vertical?'height':'width']:`${item.percentage}%` }"></div></div>
      <strong class="bar-value">{{ item.value }}</strong>
    </div>
  </div>
</template>
<style scoped>
.bars { display:grid; gap:9px; height:100%; align-content:center; }.bar-item { display:grid; grid-template-columns:76px minmax(15px,1fr) 25px; gap:8px; align-items:center; min-width:0; }.bar-label { font-size:11px; color:#9cb8d0; white-space:nowrap; }.bar-value { font:12px 'Consolas',monospace; color:#dcefff; text-align:right; }.bar-track { height:6px; background:#14344d80; border-radius:1px; overflow:hidden; }.bar-fill { background:linear-gradient(90deg,transparent,var(--bar-color)); box-shadow:0 0 8px var(--bar-color); height:100%; transition:width .5s,height .5s; }
.vertical { display:flex; align-items:stretch; gap:10px; padding-top:4px; min-height:125px; background:repeating-linear-gradient(0deg,transparent 0 30px,#376a8b20 31px 32px); }.vertical .bar-item { display:flex; flex-direction:column; flex:1; min-width:0; gap:6px; }.vertical .bar-label { order:3; white-space:normal; text-align:center; font-size:10px; line-height:1.3; min-height:26px; }.vertical .bar-value { order:1; text-align:center; }.vertical .bar-track { order:2; height:auto; flex:1; width:50%; max-width:28px; min-height:45px; display:flex; align-items:flex-end; overflow:visible; background:#0e2b4340; }.vertical .bar-fill { width:100%; background:linear-gradient(0deg,#12447b,var(--bar-color)); }
@media(prefers-reduced-motion:reduce) { .bar-fill { transition:none; } }
</style>
