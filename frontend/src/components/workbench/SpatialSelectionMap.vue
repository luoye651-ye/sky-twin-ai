<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import type { Station } from '@sky/sky'
import { boundsFromPoints, type GeoBounds, type GeoPoint } from '../../utils/spatialSelection.mjs'
const props = defineProps<{ stations: Station[]; disabled: boolean }>()
const emit = defineEmits<{ select: [bounds: GeoBounds] }>()
const anchor = shallowRef<GeoPoint>(), end = shallowRef<GeoPoint>(), error = shallowRef('')
const domain = computed(() => {
  const points = props.stations.filter(s => Number.isFinite(s.longitude) && Number.isFinite(s.latitude))
  if (!points.length) return undefined
  const minLon = Math.min(...points.map(p => p.longitude)), maxLon = Math.max(...points.map(p => p.longitude))
  const minLat = Math.min(...points.map(p => p.latitude)), maxLat = Math.max(...points.map(p => p.latitude))
  const dx = Math.max(.005,(maxLon-minLon)*.1), dy = Math.max(.005,(maxLat-minLat)*.1)
  return { minLon:minLon-dx,maxLon:maxLon+dx,minLat:minLat-dy,maxLat:maxLat+dy }
})
function project(point: GeoPoint) { const d=domain.value!; return { x:20+(point.longitude-d.minLon)/(d.maxLon-d.minLon)*560, y:340-(point.latitude-d.minLat)/(d.maxLat-d.minLat)*320 } }
const rectangle = computed(() => { if (!anchor.value || !end.value) return undefined; const a=project(anchor.value), b=project(end.value); return {x:Math.min(a.x,b.x),y:Math.min(a.y,b.y),width:Math.abs(a.x-b.x),height:Math.abs(a.y-b.y)} })
function point(event: PointerEvent): GeoPoint { const r=(event.currentTarget as SVGSVGElement).getBoundingClientRect(),d=domain.value!; const x=Math.max(20,Math.min(580,(event.clientX-r.left)/r.width*600)), y=Math.max(20,Math.min(340,(event.clientY-r.top)/r.height*360)); return {longitude:d.minLon+(x-20)/560*(d.maxLon-d.minLon),latitude:d.minLat+(340-y)/320*(d.maxLat-d.minLat)} }
function start(event: PointerEvent) { if (props.disabled || !domain.value || event.button !== 0) return; error.value=''; anchor.value=point(event); end.value=anchor.value; (event.currentTarget as SVGSVGElement).setPointerCapture(event.pointerId) }
function move(event: PointerEvent) { if (anchor.value && event.buttons) end.value=point(event) }
function finish(event: PointerEvent) { if (!anchor.value || props.disabled) return; end.value=point(event); try { emit('select',boundsFromPoints(anchor.value,end.value)) } catch(e) { error.value=String(e) } }
</script>
<template><section><p>拖动框选站点区域。此图是WGS84坐标示意，不是卫星底图；任务按起点或终点站位于区域内查询。</p><svg v-if="domain" viewBox="0 0 600 360" preserveAspectRatio="none" role="img" aria-label="站点坐标框选地图" @pointerdown="start" @pointermove="move" @pointerup="finish" @pointercancel="anchor=undefined"><rect x="0" y="0" width="600" height="360" fill="#081c2a"/><path d="M20 20V340H580" stroke="#44677d" fill="none"/><g v-for="station in stations" :key="station.id"><circle :cx="project(station).x" :cy="project(station).y" r="4" fill="#63d1ed"/><text :x="project(station).x+6" :y="project(station).y-5" fill="#d3e8f5" font-size="10">{{ station.name }}</text></g><rect v-if="rectangle" v-bind="rectangle" fill="#50d7ef22" stroke="#50d7ef" stroke-dasharray="6 3"/></svg><p v-else>尚无站点，无法框选；请刷新平台数据。</p><p v-if="error" role="alert">{{ error }}</p></section></template>
<style scoped>svg{width:100%;height:360px;display:block;touch-action:none;cursor:crosshair;border:1px solid #31546b}p{color:#9ebfd2;font-size:13px;line-height:1.8}</style>
