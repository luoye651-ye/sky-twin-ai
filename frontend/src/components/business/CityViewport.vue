<script setup lang="ts">
import { onMounted, onUnmounted, useTemplateRef, watch, shallowRef } from 'vue'
import { createCityScene, type CityAircraftLabel, type CitySceneStatus, type CityPlaceLabel } from '../../views/DigitalTwin/useCityScene'
import CitySceneControls from './CitySceneControls.vue'
import type { CityAppearance } from '../../views/DigitalTwin/cityAppearance'
import type { Aircraft, Station, Task } from '../../../../shared/sky'
import type { AirspaceCheck, AirspaceZone } from '../../../../shared/airspace'
import { connectionLabels, type PositionSample } from '@sky/positioning'
import type { RouteSketch, RouteWaypoint } from '@sky/routes'
import type { FlightNavigationDisplay } from '../../types/flightNavigation'
const props = withDefaults(defineProps<{ aircraft: Aircraft[]; stations: Station[]; tasks: Task[]; zones?: AirspaceZone[]; airspaceCheck?: AirspaceCheck; focusedZoneId?: string; positionTrack?: PositionSample[]; routeSketch?: RouteSketch; routeEditing?: boolean; flightNavigation?: FlightNavigationDisplay; overview?: boolean; selectedAircraftId?: string }>(), { zones: () => [], positionTrack: () => [], routeEditing: false, overview: false, selectedAircraftId: '' })
const emit = defineEmits<{ ready: []; routePick: [point: RouteWaypoint] }>()
const container = useTemplateRef<HTMLElement>('container')
const error = shallowRef('')
const appearance = shallowRef<CityAppearance>('dusk')
const aircraftLabels = shallowRef<CityAircraftLabel[]>([])
const placeLabels = shallowRef<CityPlaceLabel[]>([])
const traffic = shallowRef(true)
const aircraftFocusMessage = shallowRef('')
let pendingAircraftFocusId: string | undefined
const modelStatus = shallowRef<CitySceneStatus>({ phase: 'loading', message: '正在加载杭州主城区与 UAV 模型…', outsideAircraft: 0, simulatedAircraft: 0, outsideStations: 0 })
let scene: ReturnType<typeof createCityScene> | undefined
let observer: ResizeObserver | undefined
function sync() { scene?.sync(props.aircraft, props.stations, props.tasks); scene?.syncAirspace(props.zones, props.airspaceCheck); scene?.syncPositionTrack(props.positionTrack); scene?.syncRouteDraft(props.routeSketch, props.routeEditing); scene?.syncNavigation(props.flightNavigation) }
function syncFleet() { scene?.sync(props.aircraft, props.stations, props.tasks) }
function setAppearance(mode: CityAppearance) { appearance.value = mode; scene?.setAppearance(mode) }
function setTraffic(visible: boolean) { traffic.value = visible; scene?.setTraffic(visible) }
function setView(mode: 'river' | 'district' | 'overview') {
  pendingAircraftFocusId = undefined
  aircraftFocusMessage.value = ''
  if (mode === 'river') scene?.focusRiver()
  else if (mode === 'district') scene?.focusDistrict()
  else scene?.resetCamera()
}
function tryAircraftFocus() {
  const id = pendingAircraftFocusId
  if (!id) return
  const name = props.aircraft.find(a => a.id === id)?.name ?? id
  if (modelStatus.value.phase === 'error' || error.value) {
    aircraftFocusMessage.value = '场景加载失败，请重新加载后再定位。'
    return
  }
  if (modelStatus.value.phase === 'loading') {
    aircraftFocusMessage.value = `场景加载中，完成后定位${name}。`
    return
  }
  pendingAircraftFocusId = undefined
  aircraftFocusMessage.value = scene?.focusAircraft(id)
    ? `已定位${name}的地图展示位置；再次点击可重新定位。`
    : `${name}暂无可显示的位置，请检查定位数据或模型范围。`
}
function focusAircraft(id: string) {
  pendingAircraftFocusId = id
  tryAircraftFocus()
}
defineExpose({ getDiagnostics: () => scene?.getDiagnostics(), focusAircraft, focusNavigation: () => scene?.focusNavigation(), focusRouteDraft: () => scene?.focusRouteDraft(), focusPosition: (lon: number, lat: number, altitude: number) => scene?.focusPosition(lon, lat, altitude) })
onMounted(() => {
  try {
    if (!container.value) return
    scene = createCityScene(container.value, status => { modelStatus.value = status }, (labels, places) => { aircraftLabels.value = labels; placeLabels.value = places }, point => emit('routePick', point)); sync()
    observer = new ResizeObserver(() => scene?.resize()); observer.observe(container.value)
  } catch (e) { error.value = e instanceof Error ? e.message : 'WebGL 场景初始化失败' }
})
watch(() => [props.aircraft, props.stations, props.tasks], syncFleet)
watch(() => modelStatus.value.phase, phase => { tryAircraftFocus(); if (phase === 'ready') emit('ready') }, { flush: 'post' })
watch(() => [props.zones, props.airspaceCheck], () => { scene?.syncAirspace(props.zones, props.airspaceCheck) })
watch(() => props.positionTrack, points => scene?.syncPositionTrack(points))
watch(() => props.flightNavigation, display => scene?.syncNavigation(display))
watch(() => [props.routeSketch, props.routeEditing] as const, ([sketch, editing], previous) => { scene?.syncRouteDraft(sketch, editing); if (sketch && !previous?.[0]) scene?.focusRouteDraft() })
watch(() => props.airspaceCheck, () => { if (props.airspaceCheck) scene?.focusCheck() })
watch(() => props.focusedZoneId, id => { if (id) scene?.focusZone(id) })
onUnmounted(() => { observer?.disconnect(); scene?.dispose() })
</script>
<template>
  <div class="viewport" :class="{ 'viewport--overview': overview }">
    <div ref="container" class="city-canvas"></div>
    <div class="scene-label">
      <strong>杭州主城区低空态势 · 仿真</strong>
      <span>{{ modelStatus.message }}</span>
      <span>飞行器与站点状态来自 Java · 主城区外围采用 LOD · 道路车流为仿真</span>
    </div>
    <CitySceneControls v-if="modelStatus.phase === 'ready'" :appearance="appearance" :traffic="traffic" @appearance="setAppearance" @view="setView" @traffic="setTraffic" />
    <slot name="overlay" />
    <div class="aircraft-labels" aria-hidden="true">
      <div v-for="label in placeLabels" :key="label.id" class="place-label" :class="{ 'station-label': label.kind === 'station' }" :style="{ transform: `translate(${label.x}px, ${label.y}px)` }">{{ label.name }}</div>
      <div v-for="label in aircraftLabels" :key="label.id" class="aircraft-label" :class="{ 'aircraft-label--selected': label.id === selectedAircraftId }" :style="{ transform: `translate(${label.x}px, ${label.y}px)` }">
        <strong>{{ label.id }}</strong>
        <span v-if="label.positionSource">{{ label.positionSource === 'replay' ? '历史回放（仿真记录）' : `电脑仿真终端 · ${connectionLabels[label.positionState as keyof typeof connectionLabels] ?? label.positionState}` }}</span>
        <span v-if="label.simulated">仿真布点高度 {{ label.altitude.toFixed(0) }} m</span>
        <span v-else-if="label.visualized">展示高度 {{ label.altitude.toFixed(0) }} m · 业务 {{ label.reportedAltitude.toFixed(0) }} m</span>
        <span v-else>高度 {{ label.altitude.toFixed(0) }} m</span>
        <span class="battery">{{ label.positionSource ? '资源电量（非定位上报）' : '电量' }} {{ label.battery.toFixed(0) }}%</span>
      </div>
    </div>
    <div v-if="aircraftFocusMessage" class="aircraft-focus-notice" role="status">{{ aircraftFocusMessage }}</div>
    <div v-if="modelStatus.phase === 'loading' && !error" class="scene-message" role="status">{{ modelStatus.message }}</div>
    <div v-if="error || modelStatus.phase === 'error'" class="scene-message scene-error" role="alert">
      <span>{{ error || modelStatus.message }}</span>
      <button v-if="!error" class="scene-button" @click="scene?.retry()">重新加载</button>
    </div>
    <div v-if="modelStatus.phase === 'ready' && (modelStatus.outsideAircraft || modelStatus.outsideStations)" class="coordinate-notice" role="status">
      <span v-if="modelStatus.simulatedAircraft">{{ modelStatus.simulatedAircraft }} 架飞行器的坐标不在杭州主城区范围，已按仿真布点显示；Java 业务坐标未修改。</span>
      <span v-if="modelStatus.outsideStations">{{ modelStatus.outsideStations }} 个站点仍在模型范围外，相关航线暂不显示。</span>
      <span v-if="modelStatus.outsideAircraft > modelStatus.simulatedAircraft">{{ modelStatus.outsideAircraft - modelStatus.simulatedAircraft }} 架终端定位飞行器在模型范围外，未显示，未伪造场内位置。</span>
    </div>
    <div v-if="modelStatus.navigationOutside" class="navigation-outside" role="status">所选任务航线超出地图范围，未在场内伪造位置；距离数据仍来自 Java。</div>
    <div class="scene-footer">
      <span>拖动旋转 / 滚轮缩放 · WGS84 · OSM 底座 · 杭州主城区约 72 × 78 公里 · 低高度目标采用可视化抬升</span>
      <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors · ODbL</a>
      <a href="https://sketchfab.com/3d-models/delivery-drone-gameready-free-c22b1060860e47b4adbc1e9007b70b18" target="_blank" rel="noopener noreferrer">UAV: Egor Likhachev · CC BY</a>
    </div>
  </div>
</template>
<style scoped>
.viewport { position: relative; min-width: 0; min-height: 400px; height: 100%; border: 1px solid #21445b; overflow: hidden; }
.city-canvas { width: 100%; height: 100%; }
.scene-label { position: absolute; top: 18px; left: 20px; right: 360px; width: fit-content; max-width: calc(100% - 400px); display: grid; gap: 8px; padding: 12px 14px; border-radius: 5px; background: #071b2bd9; pointer-events: none; }
.scene-label strong { font-size: 16px; }
.scene-label span,.scene-footer { font-size: 12px; color: #a1c2d4; }
.scene-label span { text-shadow: 0 1px 4px #07121f; }
.scene-footer { position: absolute; bottom: 0; left: 0; right: 0; padding: 11px 20px; background: #071b2bd9; display: flex; flex-wrap: wrap; gap: 8px 20px; }
.scene-footer a { color: #a1c2d4; }
.scene-message { position: absolute; inset: 42% 20px auto; display: grid; justify-items: center; gap: 14px; color: #a1c2d4; text-align: center; }
.scene-error { color: #ff9b87; }
.scene-button { color: #a9e1fa; border: 1px solid #28546d; border-radius: 4px; background: #0b2031; padding: 7px 12px; cursor: pointer; }
.aircraft-labels { position: absolute; inset: 0; pointer-events: none; overflow: hidden; }
.aircraft-label { position: absolute; top: 0; left: 0; margin: -78px 0 0 12px; display: grid; gap: 4px; padding: 9px 13px; min-width: 100px; border: 1px solid #4aaed088; border-left: 2px solid #45d9ff; border-radius: 4px; background: #071b2bed; color: #d5f2ff; font-size: 11px; box-shadow: 0 4px 18px #0005; }
.aircraft-label strong { font-size: 13px; }.battery { color: #60eab3; }
.aircraft-label--selected { border-color:#ffd071; border-left-color:#ffd071; z-index:1; box-shadow:0 0 18px #ffc85755; }
.aircraft-focus-notice { position:absolute; top:158px; right:18px; max-width:300px; padding:9px 12px; border:1px solid #55d3ff77; border-radius:4px; background:#071b2bed; color:#bcefff; font-size:12px; line-height:1.6; pointer-events:none; }
.place-label { position: absolute; top: 0; left: 0; padding: 5px 8px; border-left: 2px solid #7ad6da; border-radius: 3px; background: #082638cc; font-size: 12px; color: #cff1ec; white-space: nowrap; }
.station-label { margin: -34px 0 0 10px; border: 1px solid #ffc85c99; border-left: 3px solid #ffc85c; background: #182619ee; color: #fff0b3; font-weight: 700; box-shadow: 0 3px 12px #0007; }
.coordinate-notice { position: absolute; bottom: 68px; left: 20px; right: 20px; width: fit-content; max-width: calc(100% - 40px); padding: 10px 14px; background: #142435ed; border: 1px solid #8d7540; border-radius: 4px; color: #efd49c; font-size: 12px; line-height: 1.6; }
.coordinate-notice span { display: block; }
.navigation-outside { position:absolute; right:18px; bottom:70px; max-width:340px; padding:10px; background:#142435ed; color:#efd49c; font-size:12px; }
@media (max-width: 1100px) {
  .scene-label { top: 98px; right: 20px; max-width: calc(100% - 40px); }
  .scene-label strong { font-size: 14px; }
  .aircraft-focus-notice { top:205px; right:14px; max-width:260px; }
}
.viewport--overview { min-height:0; border:0; }
.viewport--overview .scene-label { top:12px; left:12px; right:12px; max-width:calc(100% - 24px); width:auto; gap:5px; padding:10px; background:linear-gradient(90deg,#041a2de8,#041a2d88); }
.viewport--overview .scene-label strong { font-size:14px; color:#d8efff; }
.viewport--overview .scene-label span { font-size:10px; }
.viewport--overview :deep(.view-controls) { top:auto; bottom:92px; left:12px; right:12px; gap:5px; }
.viewport--overview :deep(.scene-button) { padding:5px 7px; font-size:10px; }
.viewport--overview .scene-footer { font-size:9px; padding:8px 12px; gap:5px 10px; }
.viewport--overview .coordinate-notice { bottom:175px; left:12px; right:12px; max-width:calc(100% - 24px); font-size:10px; padding:7px 9px; }
</style>
