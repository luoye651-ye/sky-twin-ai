<script setup lang="ts">
import { aircraftTypes, statusLabels, type Aircraft, type Task } from '../../../../shared/sky'
import { computed } from 'vue'
import { connectionLabels } from '@sky/positioning'
const props = withDefaults(defineProps<{ aircraft: Aircraft[]; tasks: Task[]; connected: boolean; selectedId?: string }>(), { selectedId: '' })
const emit = defineEmits<{ locate: [aircraftId: string] }>()
const activeTasks = computed(() => Object.fromEntries(props.aircraft.map(a => [a.id, props.tasks.filter(t => t.aircraftId === a.id && ['assigned', 'executing'].includes(t.status))])))
</script>
<template>
  <aside class="fleet-panel"><div class="fleet-heading"><h3>飞行器资源</h3><span :class="{ live: connected }">{{ connected ? '实时' : '重连中' }}</span></div>
    <p class="fleet-hint">点击飞行器，在地图中定位</p>
    <article v-for="a in aircraft" :key="a.id" class="fleet-card" :class="{ 'fleet-card--selected': selectedId === a.id }" role="button" tabindex="0" :aria-pressed="selectedId === a.id" :aria-label="`定位${a.name}（${a.id}）`" @click="emit('locate', a.id)" @keydown.enter.prevent="emit('locate', a.id)" @keydown.space.prevent="emit('locate', a.id)"><div class="fleet-title"><strong>{{ a.name }}</strong><span>{{ statusLabels[a.status] }}</span></div><p>{{ aircraftTypes[a.type] }} · {{ a.model }}</p>
      <div class="fleet-metrics"><span>电量 {{ a.battery.toFixed(1) }}%</span><span>高度 {{ a.altitude.toFixed(0) }}m</span><span>速度 {{ a.speed.toFixed(1) }}m/s</span><span>{{ a.type === 'evtol' ? `${a.seats} 座` : `${a.payloadCapacity} kg 载重` }}</span></div>
      <small>{{ a.longitude.toFixed(6) }}, {{ a.latitude.toFixed(6) }}</small>
      <p v-if="a.positionSource">电脑仿真终端 · {{ connectionLabels[a.positionState as keyof typeof connectionLabels] ?? a.positionState }}<br />电量/速度为原资源值，非终端上报</p>
      <div v-for="task in activeTasks[a.id]" :key="task.id" class="fleet-task"><span>{{ task.title }}</span><el-progress :percentage="Number(task.progress.toFixed(1))" :stroke-width="4" /></div>
    </article><p v-if="!aircraft.length" class="empty-note">暂无飞行器，请在业务管理中添加。</p><RouterLink to="/task-management" class="dispatch-link">前往任务调度 →</RouterLink>
  </aside>
</template>
<style scoped>
.fleet-panel { padding: 18px; overflow: auto; background: #081725; border: 1px solid #21445b; }.fleet-heading,.fleet-title { display: flex; justify-content: space-between; gap: 8px; align-items: center; }.fleet-heading h3 { margin: 0; font-size: 16px; }.fleet-heading span { color: #db9e43; font-size: 12px; }.fleet-heading .live { color: #25e6ad; }
.fleet-card { padding: 15px; margin-top: 14px; border: 1px solid #22445c; border-radius: 6px; background: #102235; }.fleet-title { font-size: 13px; }.fleet-title span,.fleet-card p,.fleet-card small { color: #87acc3; font-size: 12px; }.fleet-metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 12px; margin: 14px 0; }.fleet-task { margin-top: 12px; font-size: 12px; }.dispatch-link { display: block; margin-top: 20px; color: #55d3ff; font-size: 13px; }
.fleet-hint { margin:10px 0 0; font-size:11px; color:#87acc3; }
.fleet-card { cursor:pointer; transition:border-color .15s, background-color .15s, box-shadow .15s; }
.fleet-card:hover { border-color:#55d3ff; background:#132d42; }
.fleet-card--selected { border-color:#55d3ff; box-shadow:inset 3px 0 #55d3ff,0 0 14px #25bbed26; }
.fleet-card:focus-visible { outline:2px solid #ffd071; outline-offset:3px; }
</style>
