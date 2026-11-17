<script setup lang="ts">
defineProps<{ items: { key:string; label:string; value:number|null; color:string; name:string }[]; average:number|null }>()
</script>
<template>
  <div class="battery-summary"><span>机队平均电量</span><strong>{{ average === null ? '—' : average.toFixed(1)+'%' }}</strong></div>
  <div v-if="items.length" class="battery-list" role="list">
    <div v-for="item in items" :key="item.key" class="battery-row" role="listitem" :aria-label="`${item.name}电量${item.value ?? '未知'}`" :title="item.name">
      <span class="battery-id">{{ item.label }}</span><div class="battery-track"><div :style="{ width:`${item.value ?? 0}%`, background:item.color }"></div></div><strong>{{ item.value === null ? '—' : item.value.toFixed(1)+'%' }}</strong>
    </div>
  </div>
  <p v-else class="battery-empty">暂无飞行器电量数据</p>
</template>
<style scoped>
.battery-summary { display:flex; justify-content:space-between; align-items:center; gap:6px; color:#93afc4; font-size:10px; margin-bottom:10px; }.battery-summary strong { color:#50e8c2; font:20px 'Consolas',monospace; text-shadow:0 0 10px #27d5af55; }.battery-list { display:grid; gap:10px; max-height:105px; overflow:auto; scrollbar-width:thin; }.battery-row { display:grid; grid-template-columns:minmax(35px,70px) minmax(30px,1fr) 45px; align-items:center; gap:8px; }.battery-id { color:#a3bed4; font-size:10px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.battery-track { height:7px; background:#153349; border-radius:1px; overflow:hidden; }.battery-track>div { height:100%; opacity:.9; box-shadow:0 0 8px #26d5b466; transition:width .5s; }.battery-row strong { font:11px 'Consolas',monospace; color:#d4f4ed; text-align:right; }.battery-empty { color:#80a4bd; font-size:12px; text-align:center; padding:15px 0; }@media(prefers-reduced-motion:reduce) { .battery-track>div { transition:none; } }
</style>
