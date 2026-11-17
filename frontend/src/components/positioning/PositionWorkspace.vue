<script setup lang="ts">
import { computed, useTemplateRef, watch } from 'vue'
import { useSkyStore } from '../../stores/sky'
import { usePositioning } from '../../composables/usePositioning'
import { usePositionReplay } from '../../composables/usePositionReplay'
import CityViewport from '../business/CityViewport.vue'
import PositionDevicePanel from './PositionDevicePanel.vue'
import PositionSenderPanel from './PositionSenderPanel.vue'
import PositionReplayPanel from './PositionReplayPanel.vue'
import BeidouDemoPanel from './BeidouDemoPanel.vue'
const sky = useSkyStore()
const p = usePositioning(() => sky.snapshot.aircraft), r = usePositionReplay()
const { devices, selectedId, selected, receipts, busy, sending, running, error, notice } = p
const { points, active, playing, loading, offset, speed, duration, at, position, hasMore, error: replayError } = r
const viewport = useTemplateRef<InstanceType<typeof CityViewport>>('viewport')
const canManage = computed(() => sky.permissions.includes('*:*:*') || sky.permissions.includes('sky:manage'))
const track = computed(() => active.value ? points.value : receipts.value.filter(x => x.accepted && x.sessionId === selected.value?.sessionId).reverse())
const displayAircraft = computed(() => sky.snapshot.aircraft.map(a => active.value && position.value && a.id === selected.value?.aircraftId ? { ...a, ...position.value, positionSource: 'replay' as const, positionState: 'replay', positionSampledAt: new Date(at.value).toISOString() } : a))
function focus() {
  const point = active.value ? position.value : selected.value
  if (point && point.longitude != null && point.latitude != null) viewport.value?.focusPosition(point.longitude, point.latitude, point.altitude ?? 0)
}
async function load(from: string, to: string) { if (selectedId.value) { p.stop(); await r.load(selectedId.value, from, to); focus() } }
watch(selectedId, r.reset)
function start(protocol: 'json' | 'nmea' = 'json') { r.reset(); p.start(protocol); focus() }
function send(kind: 'normal' | 'no_fix' | 'delay' | 'jump' | 'duplicate') { r.reset(); void p.send(kind) }
async function sendNmea(kind: 'normal' | 'no_fix' | 'bad_checksum') { r.reset(); await p.send(kind, undefined, 'nmea'); focus() }
</script>
<template>
  <section class="workspace business-theme"><div class="page-heading"><div><span class="eyebrow">POSITIONING · SIMULATION VALIDATION</span><h1>定位接入与轨迹回放</h1><p>电脑模拟终端 → Java 校验与持久化 → 实时地图 → 历史回放</p></div><el-button :disabled="!selected" @click="focus">定位当前飞行器</el-button></div>
    <el-alert title="仿真验证版：未接北斗/GNSS硬件，不代表真实定位精度或实机飞控能力。坐标约定WGS84，高度为相对起飞点米数；地图使用平面底座，非真实地形净空。" type="warning" :closable="false" />
    <el-alert v-if="error" :title="error" type="error" :closable="false" /><el-alert v-if="notice" :title="notice" type="info" :closable="false" />
    <PositionDevicePanel :devices="devices" :aircraft="sky.snapshot.aircraft" :selected-id="selectedId" :busy="busy || sending" :can-manage="canManage" :can-operate="sky.canOperate" @select="selectedId = $event" @bind="p.bind" @mode="r.reset(); p.mode($event)" />
    <BeidouDemoPanel :enabled="!!selected?.enabled" :running="running" :sending="sending || busy" :can-operate="sky.canOperate" :nmea-running="running && p.senderProtocol.value === 'nmea'" :frame="p.nmeaFrame.value" :result="p.nmeaResult.value" @preview="p.previewNmea" @start="start('nmea')" @stop="p.stop" @send="sendNmea" />
    <div class="map"><CityViewport ref="viewport" :aircraft="displayAircraft" :stations="sky.snapshot.stations" :tasks="sky.snapshot.tasks" :zones="sky.snapshot.airspaceZones" :position-track="track" /><div class="watermark">{{ active ? '历史回放 · 不影响实时状态' : '实时定位 · 电脑仿真数据' }}</div></div>
    <PositionSenderPanel :enabled="!!selected?.enabled" :running="running" :sending="sending || busy" :can-operate="sky.canOperate" :receipts="receipts" @start="start()" @stop="p.stop" @send="send" />
    <PositionReplayPanel :selected="!!selected" :active="active" :playing="playing" :loading="loading" :offset="offset" :duration="duration" :at="at" :speed="speed" :count="points.length" :held="!!position?.held" :has-more="hasMore" :error="replayError" @load="load" @play="r.play" @pause="r.pause" @exit="r.reset" @seek="r.seek" @speed="speed = $event" />
  </section>
</template>
<style scoped>.workspace { padding:24px; display:grid; gap:18px; min-height:100%; }.page-heading { margin-bottom:0; }.map { height:560px; min-height:400px; position:relative; }.watermark { position:absolute; bottom:62px; right:18px; padding:10px 14px; background:#071b2bf0; border:1px solid #f5bb57; color:#f5d38e; font-size:13px; pointer-events:none; }</style>
