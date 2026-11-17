<script setup lang="ts">
import { computed } from 'vue'
import { ringSegments, type ChartDatum } from '../../utils/overviewMetrics'
const props = defineProps<{ items: ChartDatum[]; total: number; label: string }>()
const segments = computed(() => ringSegments(props.items))
</script>
<template>
  <div class="ring-chart">
    <div class="ring-dial">
      <svg viewBox="0 0 120 120" role="img" :aria-label="`${label} ${total}，${items.map(i => `${i.label}${i.value}`).join('，')}`">
        <circle class="dial-guide" cx="60" cy="60" r="56" /><circle class="dial-track" cx="60" cy="60" r="44" />
        <circle v-for="s in segments" :key="s.key" cx="60" cy="60" r="44" pathLength="100" fill="none" :stroke="s.color" stroke-width="8" :stroke-dasharray="`${s.percent} ${100-s.percent}`" :stroke-dashoffset="-s.offset" transform="rotate(-90 60 60)"><title>{{ s.label }} {{ s.value }}</title></circle>
      </svg>
      <div class="dial-value"><strong>{{ total }}</strong><span>{{ label }}</span></div>
    </div>
    <ul class="ring-legend"><li v-for="item in items" :key="item.key"><i :style="{ background:item.color }"></i><span>{{ item.label }}</span><strong>{{ item.value }}</strong></li></ul>
  </div>
</template>
<style scoped>
.ring-chart { display:flex; align-items:center; justify-content:space-evenly; gap:12px; min-height:126px; }.ring-dial { width:clamp(95px,8vw,138px); flex-shrink:0; position:relative; }.ring-dial svg { display:block; width:100%; overflow:visible; filter:drop-shadow(0 0 5px #22b6ff2a); }.dial-guide { fill:none; stroke:#24608b; stroke-dasharray:2 5; stroke-width:1; }.dial-track { fill:#061827; stroke:#16384e; stroke-width:8; }.dial-value { position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:4px; pointer-events:none; }.dial-value strong { color:#e3faff; font:600 28px 'Bahnschrift','Consolas',sans-serif; text-shadow:0 0 14px #45c4ff88; }.dial-value span { font-size:10px; color:#88b1cb; }.ring-legend { padding:0; margin:0; list-style:none; min-width:95px; flex:1; max-width:155px; display:grid; gap:9px; }.ring-legend li { display:flex; align-items:center; gap:7px; font-size:11px; color:#a9c3d7; }.ring-legend i { width:5px; height:5px; border-radius:1px; flex-shrink:0; }.ring-legend strong { margin-left:auto; color:#e1f7ff; font:600 13px 'Consolas',monospace; }
</style>
