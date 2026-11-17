<script setup lang="ts">
import { computed } from 'vue'
import { statusLabels, type Task } from '@sky/sky'
import { formatFlightDistance } from '../../utils/flightNavigation'
const props = defineProps<{ tasks: Task[]; selected?: Task; selectedId: string; connected: boolean; available: boolean; trackError: string }>()
const emit = defineEmits<{ select: [id: string]; focusRoute: []; locate: [] }>()
const nav = computed(() => props.available ? props.selected?.navigation : undefined)
const progress = computed(() => Math.max(0, Math.min(100, props.selected?.progress ?? 0)))
const stopped = computed(() => ['cancelled', 'failed'].includes(props.selected?.status ?? ''))
</script>

<template>
  <section class="flight-navigation" aria-label="物流任务地图跟踪">
    <header><strong>物流任务 · 地图跟踪</strong><span :class="{ offline: !connected }">{{ connected ? '实时仿真' : '连接中断 · 数据已暂停' }}</span></header>
    <el-select :model-value="selectedId" placeholder="选择配送任务" aria-label="选择地图跟踪任务" filterable @update:model-value="emit('select', $event)">
      <el-option v-for="task in tasks" :key="task.id" :value="task.id" :label="`${task.title} · ${statusLabels[task.status] ?? task.status}`" />
    </el-select>
    <p v-if="!selected" class="notice">{{ selectedId ? '此任务不存在或不在当前可查看的物流任务中。' : '暂无执行中的配送，请选择任务或前往物流运输创建配送。' }}</p>
    <template v-else>
      <p class="route-name">{{ selected.startStationName }} → {{ selected.endStationName }}</p>
      <div class="flight-meta"><span>{{ selected.aircraftName || '尚未分配飞行器' }}</span><span>{{ statusLabels[selected.status] ?? selected.status }}</span></div>
      <el-progress :percentage="Number(progress.toFixed(1))" :stroke-width="5" />
      <template v-if="nav">
        <div class="distance-grid">
          <div><span>{{ stopped ? '停止处剩余航程' : '沿航线剩余' }}</span><strong data-testid="remaining-route">{{ formatFlightDistance(nav.remainingRouteMeters) }}</strong></div>
          <div><span>距终点直线</span><strong data-testid="destination-distance">{{ formatFlightDistance(nav.destinationDistanceMeters) }}</strong></div>
        </div>
        <p class="position" data-testid="navigation-position">{{ stopped ? '停止位置' : selected.status === 'completed' ? '任务终点' : selected.status === 'executing' ? '当前位置' : '计划起点' }}：{{ nav.position.longitude.toFixed(6) }}, {{ nav.position.latitude.toFixed(6) }}<br>高度 {{ nav.position.altitude.toFixed(0) }} m</p>
        <div class="navigation-actions"><el-button size="small" @click="emit('focusRoute')">查看完整航线</el-button><el-button size="small" @click="emit('locate')">定位任务位置</el-button></div>
      </template>
      <p v-else class="notice">暂无导航数据，请确认 Java 服务已更新并重新连接。</p>
      <p v-if="stopped" class="notice">任务已停止，保留最后位置和历史轨迹，不再推进。</p>
      <p v-if="selected.status === 'completed'" class="notice">仿真飞行已完成；送达确认请在物流运输中操作。</p>
    </template>
    <p v-if="trackError" class="notice" role="alert">已飞轨迹更新失败，当前轨迹可能不是最新数据：{{ trackError }}</p>
    <div class="legend"><span class="planned">计划航线</span><span class="flown">已飞轨迹</span><span class="remaining">剩余路线</span></div>
    <small>Java 仿真位置 · WGS84 水平距离 · 已飞轨迹每 3 秒更新</small>
  </section>
</template>

<style scoped>
.flight-navigation { position:absolute; z-index:2; bottom:60px; left:18px; width:335px; max-width:calc(100% - 36px); max-height:calc(100% - 220px); overflow:auto; padding:16px; border:1px solid #2e6682; border-radius:8px; background:#071b2bf2; box-shadow:0 8px 28px #0005; color:#d5efff; }
header,.flight-meta,.navigation-actions { display:flex; justify-content:space-between; gap:8px; align-items:center; }header { margin-bottom:12px; }header strong { font-size:14px; }header span { color:#36e5ac; font-size:11px; }header .offline,.notice { color:#ffc857; }.el-select { width:100%; }
.route-name { margin:12px 0 8px; font-size:13px; line-height:1.6; }.flight-meta,.position { color:#9abacf; font-size:12px; }.flight-meta { margin-bottom:10px; }.distance-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin:14px 0 10px; }.distance-grid span { display:block; font-size:12px; color:#a2bdce; }.distance-grid strong { display:block; font-size:23px; color:#ffc857; margin-top:5px; }.position,.notice { font-size:12px; line-height:1.7; }.navigation-actions { justify-content:flex-start; flex-wrap:wrap; }.legend { display:flex; gap:14px; margin:14px 0 8px; font-size:12px; }.legend span:before { content:''; display:inline-block; width:13px; border-top:3px solid; vertical-align:middle; margin-right:5px; }.planned { color:#38cfff; }.flown { color:#33e8a5; }.remaining { color:#ffc857; }small { color:#86a9bf; font-size:10px; }
@media(max-width:700px) { .flight-navigation { width:280px; left:10px; bottom:80px; padding:12px; max-height:55%; }.distance-grid strong { font-size:20px; } }
</style>
