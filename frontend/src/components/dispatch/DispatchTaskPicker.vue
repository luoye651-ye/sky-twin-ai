<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Aircraft, Task } from '@sky/sky'
import { taskTypes, aircraftTypes } from '@sky/sky'
import type { DispatchRequest } from '@sky/dispatch'
const props = defineProps<{ tasks: Task[]; aircraft: Aircraft[]; busy: boolean; canOperate: boolean }>()
const emit = defineEmits<{ generate: [request: DispatchRequest] }>()
const selected = ref<string[]>([])
const priorities = ref<Record<string, number>>({})
const fleetIds = ref<string[]>([])
const pending = computed(() => props.tasks.filter(task => task.status === 'created'))
const selectedTasks = computed(() => pending.value.filter(task => selected.value.includes(task.id)))
const fleet = computed(() => props.aircraft.filter(aircraft => fleetIds.value.includes(aircraft.id)))
const invalid = computed(() => selectedTasks.value.length === 0 || selectedTasks.value.length > 20 || fleet.value.length === 0)
function selectAll() { selected.value = pending.value.slice(0, 20).map(task => task.id) }
function generate() {
  if (props.busy || !props.canOperate || invalid.value) return
  emit('generate', { tasks: selectedTasks.value.map(task => ({ taskId: task.id, priority: priorities.value[task.id] ?? task.responsePriority ?? 1 })), aircraftIds: fleet.value.map(value => value.id) })
}
</script>
<template>
  <section class="picker">
    <div class="title-row"><h2>1. 选择任务和资源</h2><el-button :disabled="busy || !canOperate" @click="selectAll">选取前20项待分配任务</el-button></div>
    <p class="hint">本批优先级只影响本次优化：先最大化可分配任务数，再优先高等级任务，最后降低综合成本。已复核环境应急任务按等级设置服务端优先级下限，不抢占正在执行的任务。</p>
    <div class="task-list">
      <div v-for="task in pending" :key="task.id" class="task-row">
        <el-checkbox v-model="selected" :value="task.id" :disabled="busy || !canOperate" :aria-label="`选择任务 ${task.title}`" />
        <div class="task-info"><strong>{{ task.title }}</strong><span>{{ taskTypes[task.type] }} · {{ task.startStationName }} → {{ task.endStationName }} · {{ task.payload }} kg<template v-if="task.passengers"> · {{ task.passengers }} 人</template></span></div>
        <el-select :model-value="priorities[task.id] ?? task.responsePriority ?? 1" :disabled="busy || !canOperate" :aria-label="`任务优先级 ${task.title}`" class="priority" @update:model-value="priorities[task.id] = $event"><el-option label="普通" :value="1" :disabled="(task.responsePriority ?? 1) > 1" /><el-option label="优先" :value="2" :disabled="(task.responsePriority ?? 1) > 2" /><el-option label="紧急" :value="3" /></el-select>
      </div>
      <el-empty v-if="!pending.length" description="暂无待分配任务，请先创建任务或配送订单" :image-size="65" />
    </div>
    <div class="title-row fleet-heading"><h3>参与评估的飞行器</h3><el-button :disabled="busy || !canOperate" @click="fleetIds = aircraft.map(value => value.id)">选择全部资源</el-button></div>
    <div class="fleet-list"><el-checkbox v-for="aircraft in aircraft" :key="aircraft.id" v-model="fleetIds" :value="aircraft.id" :disabled="busy || !canOperate" :aria-label="`选择资源 ${aircraft.name}`">{{ aircraft.name }} · {{ aircraftTypes[aircraft.type] }} · {{ aircraft.battery.toFixed(0) }}% · {{ aircraft.status === 'idle' ? '空闲' : '占用' }}</el-checkbox></div>
    <div class="generate-row"><span class="hint">已选 {{ selectedTasks.length }} / 20 项任务 · {{ fleet.length }} 架飞行器</span><el-button type="primary" :loading="busy" :disabled="invalid || !canOperate" @click="generate">生成集群调度方案</el-button></div>
  </section>
</template>
<style scoped>
.picker { background:#0b2132; border:1px solid #24465d; border-radius:8px; padding:20px; }.title-row,.generate-row { display:flex; align-items:center; justify-content:space-between; gap:12px; }.title-row h2 { font-size:18px; margin:0; }.hint { color:#90b4cb; font-size:12px; line-height:1.7; }.task-list { max-height:330px; overflow:auto; }.task-row { display:flex; align-items:center; gap:12px; padding:12px 0; border-bottom:1px solid #244052; }.task-info { display:grid; gap:6px; min-width:0; flex:1; }.task-info span { color:#92b4ca; font-size:12px; }.priority { width:100px; }.fleet-heading { margin-top:16px; }.fleet-heading h3 { font-size:14px; }.fleet-list { display:grid; gap:6px; }.fleet-list :deep(.el-checkbox__label) { color:#b6d8e9; white-space:normal; }.generate-row { margin-top:20px; }@media(max-width:900px) { .title-row,.generate-row { flex-wrap:wrap; } }
</style>
