<script setup lang="ts">
import type { Task } from '@sky/sky'
defineProps<{ tasks: Task[]; selected: string[]; disabled: boolean }>()
defineEmits<{ toggle: [id: string]; move: [index: number, direction: number] }>()
</script>
<template>
  <section class="card"><h2>1 · 选择已分配任务（最多20项）</h2><p>按下方顺序优先安排时隙，不抢占正在执行的任务。先在任务管理或 Agent 指挥中分配飞行器。</p>
    <div class="choices"><label v-for="t in tasks" :key="t.id"><input type="checkbox" :aria-label="`选择${t.title}`" :checked="selected.includes(t.id)" :disabled="disabled || (!selected.includes(t.id) && selected.length >= 20)" @change="$emit('toggle', t.id)">{{ t.title }} · {{ t.aircraftId }} · v{{ t.routeRevision ?? 0 }}</label><span v-if="!tasks.length">暂无可预约任务。</span></div>
    <ol><li v-for="(id, index) in selected" :key="id">{{ tasks.find(t => t.id === id)?.title ?? id }} <el-button :disabled="disabled || index === 0" @click="$emit('move', index, -1)">上移</el-button><el-button :disabled="disabled || index === selected.length - 1" @click="$emit('move', index, 1)">下移</el-button></li></ol>
  </section>
</template>
<style scoped>.card { padding:18px; border:1px solid #21445b; background:#0b1d2d; }.card h2 { font-size:17px; margin:0 0 12px; }.card p,.choices { font-size:13px; color:#acc7d8; }.choices { display:flex; flex-wrap:wrap; gap:16px; max-height:220px; overflow:auto; }.choices label { display:flex; gap:8px; align-items:center; }.card li { margin:10px 0; font-size:13px; }</style>
