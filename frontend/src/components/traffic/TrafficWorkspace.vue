<script setup lang="ts">
import { computed, nextTick, shallowRef, useTemplateRef, watch } from 'vue'
import { useSkyStore } from '../../stores/sky'
import { useTrafficPlanning } from '../../composables/useTrafficPlanning'
import type { TrafficConflict } from '@sky/traffic'
import type { RouteSketch } from '@sky/routes'
import CityViewport from '../business/CityViewport.vue'
import TrafficTaskPicker from './TrafficTaskPicker.vue'
import TrafficPlanResult from './TrafficPlanResult.vue'
import TrafficReservations from './TrafficReservations.vue'
const sky = useSkyStore(), t = useTrafficPlanning(() => sky.refresh())
const { state, plan, busy, error, notice } = t
const selected = shallowRef<string[]>([]), lead = shallowRef(15), maxDelay = shallowRef(120), reason = shallowRef('人工确认多机错峰起飞')
const hit = shallowRef<TrafficConflict>(), viewport = useTemplateRef<InstanceType<typeof CityViewport>>('viewport')
const tasks = computed(() => sky.snapshot.tasks.filter(task => task.status === 'assigned' && !state.value?.slots.some(s => s.taskId === task.id && s.status === 'reserved')))
const staleSelection = computed(() => selected.value.some(id => !tasks.value.some(task => task.id === id)))
const sketch = computed<RouteSketch | undefined>(() => hit.value ? { points: [hit.value, hit.value], waypoints: [hit.value], altitude: hit.value.altitude, selected: -1 } : undefined)
function toggle(id: string) { if (busy.value) return; selected.value = selected.value.includes(id) ? selected.value.filter(x => x !== id) : [...selected.value, id]; t.invalidate() }
function move(index: number, direction: number) { if (busy.value) return; const next = [...selected.value], target = index + direction; if (!next[index] || !next[target]) return; [next[index], next[target]] = [next[target]!, next[index]!]; selected.value = next; t.invalidate() }
function preview() { return t.preview({ tasks: selected.value.map(id => ({ taskId: id, expectedRevision: tasks.value.find(task => task.id === id)?.routeRevision ?? 0 })), leadSeconds: lead.value, maxDelaySeconds: maxDelay.value }) }
async function focus(value: TrafficConflict) { hit.value = value; await nextTick(); viewport.value?.focusPosition(value.longitude, value.latitude, value.altitude) }
watch([lead, maxDelay], () => t.invalidate())
</script>
<template>
  <section class="workspace business-theme"><div class="page-heading"><div><span class="eyebrow">MULTI-AIRCRAFT DECONFLICTION · SIMULATION</span><h1>多机协同 · 冲突预测与错峰起飞</h1><p>保存航线 → 预测时空冲突 → 人工确认预约 → 服务端到点复核起飞</p></div><RouterLink to="/route-planning">航线规划 →</RouterLink></div>
    <el-alert title="仿真第一版：水平100m + 投影保护带10m、垂直30m，属于演示参数，不是法定安全间隔。不包含实机避障、建筑净空、动态改线或未接入飞行器。Java暂停/重启时仿真时钟和所有预约一起暂停。" type="warning" :closable="false" />
    <el-alert v-if="error" :title="error" type="error" :closable="false" /><el-alert v-if="notice" :title="notice" type="success" :closable="false" />
    <div class="toolbar"><strong>仿真 tick：{{ state?.clockTick ?? '读取中' }}</strong><span>约每个服务端周期前进1秒；并非真实飞行时间</span><el-button :disabled="busy" @click="t.refresh">刷新预约</el-button><RouterLink to="/task-management">分配 / 终止任务 →</RouterLink></div>
    <TrafficTaskPicker :tasks="tasks" :selected="selected" :disabled="busy || !sky.canOperate" @toggle="toggle" @move="move" />
    <div class="settings"><label>提前量（仿真秒）<input v-model.number="lead" aria-label="起飞提前量" type="number" min="5" max="300" :disabled="busy || !sky.canOperate"></label><label>最大额外等待（秒）<input v-model.number="maxDelay" aria-label="最大错峰等待" type="number" min="0" max="600" :disabled="busy || !sky.canOperate"></label><label class="reason">操作原因<input v-model="reason" aria-label="错峰操作原因" maxlength="500" :disabled="busy || !sky.canOperate"></label><el-button type="primary" :disabled="busy || !sky.canOperate || !selected.length || staleSelection" @click="preview">预测冲突并生成错峰方案</el-button><el-button :disabled="busy" @click="selected = []; t.invalidate()">清空选择</el-button></div>
    <p v-if="staleSelection" class="warning">所选任务已被预约或状态变化，请清空后重新选择。</p>
    <TrafficPlanResult :plan="plan" :busy="busy" :can-operate="sky.canOperate" :reason="reason" @confirm="t.confirm(reason)" @focus="focus" />
    <div class="map"><CityViewport ref="viewport" :aircraft="sky.snapshot.aircraft" :stations="sky.snapshot.stations" :tasks="sky.snapshot.tasks" :zones="sky.snapshot.airspaceZones" :route-sketch="sketch" /><span v-if="hit" class="map-note">黄色标记：未错峰方案的预计冲突点 · {{ hit.longitude.toFixed(6) }}, {{ hit.latitude.toFixed(6) }} · {{ hit.altitude.toFixed(1) }}m</span></div>
    <TrafficReservations :state="state" :busy="busy" :can-operate="sky.canOperate" :reason="reason" @cancel="t.cancel($event, reason)" @load="t.load" />
  </section>
</template>
<style scoped>.workspace { padding:24px; display:grid; gap:18px; }.page-heading { margin-bottom:0; }.toolbar,.settings { display:flex; flex-wrap:wrap; gap:16px; align-items:center; }.toolbar span,.toolbar a { font-size:13px; color:#acc7d8; }.settings { align-items:end; }.settings label { display:grid; gap:8px; color:#acc7d8; font-size:13px; }.settings input { background:#102a3d; color:#d8effa; border:1px solid #31546b; padding:10px; width:160px; }.settings .reason input { width:300px; }.warning { color:#ffcf83; }.map { height:500px; position:relative; }.map-note { position:absolute; bottom:65px; left:20px; padding:10px; color:#ffdb88; background:#071b2bed; font-size:12px; }</style>
