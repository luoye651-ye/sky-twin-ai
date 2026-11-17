<script setup lang="ts">
import { defineAsyncComponent, nextTick, shallowRef, useTemplateRef, watch } from 'vue'
import type { AgentMapTarget } from '../../types/agent'
import type { RouteSketch } from '@sky/routes'
import { useSkyStore } from '../../stores/sky'
import { getRoute } from '../../api/routes'
const CityViewport = defineAsyncComponent(() => import('../business/CityViewport.vue'))
const props = defineProps<{ target: AgentMapTarget }>()
const sky = useSkyStore(), error = shallowRef(''), sketch = shallowRef<RouteSketch>()
const viewport = useTemplateRef<InstanceType<typeof CityViewport>>('viewport')
async function focus() {
  if (props.target.kind === 'aircraft') viewport.value?.focusAircraft(props.target.id)
  else viewport.value?.focusRouteDraft()
}
watch(() => props.target, async (target, _old, cleanup) => {
  let stale = false; cleanup(() => { stale = true })
  error.value = ''; sketch.value = undefined
  try {
    if (target.kind === 'task') {
      const detail = await getRoute(target.id)
      if (stale) return
      sketch.value = { points: detail.plan.points, waypoints: detail.plan.waypoints, altitude: detail.plan.cruiseAltitude, selected: -1 }
    } else if (!sky.snapshot.aircraft.some(a => a.id === target.id)) throw new Error('当前快照中没有这架飞机，请刷新后重试')
    if (!stale) { await nextTick(); await focus() }
  } catch (e) { if (!stale) error.value = e instanceof Error ? e.message : '地图对象读取失败' }
}, { immediate: true })
// Async component creation and model loading may finish after the first focus request.
watch(viewport, () => { void focus() })
</script>
<template>
  <section class="context-map">
    <p>{{ target.label }} · {{ target.id }} <el-button @click="focus">重新定位</el-button></p>
    <p v-if="error" role="alert">{{ error }}</p>
    <div v-else class="map"><CityViewport ref="viewport" @ready="focus" :aircraft="sky.snapshot.aircraft" :stations="sky.snapshot.stations" :tasks="sky.snapshot.tasks" :zones="sky.snapshot.airspaceZones" :route-sketch="sketch" :selected-aircraft-id="target.kind === 'aircraft' ? target.id : ''" /></div>
  </section>
</template>
<style scoped>.context-map p{color:#a8cde0;font-size:13px;overflow-wrap:anywhere}.map{height:540px;min-height:360px}</style>
