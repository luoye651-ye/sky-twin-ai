<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { useSkyStore } from '../../stores/sky'
import { useAirspace } from '../../composables/useAirspace'
import type { AirspaceZone, AirspaceZoneInput } from '@sky/airspace'
import CityViewport from '../business/CityViewport.vue'
import AirspaceZoneEditor from './AirspaceZoneEditor.vue'
import AirspaceZoneTable from './AirspaceZoneTable.vue'
import AirspaceCheckPanel from './AirspaceCheckPanel.vue'
import AirspaceCheckHistory from './AirspaceCheckHistory.vue'
const sky = useSkyStore()
const canManage = computed(() => sky.permissions.includes('*:*:*') || sky.permissions.includes('sky:manage'))
const { zones, checks, result, busy, error, notice, refresh, save, check, open } = useAirspace(() => sky.refresh())
const editor = shallowRef(false)
const selected = shallowRef<AirspaceZone>()
const focusedZoneId = shallowRef('')
function edit(zone?: AirspaceZone) { selected.value = zone; editor.value = true }
function focus(id: string) { focusedZoneId.value = id }
async function submit(input: AirspaceZoneInput) { if (await save(input, selected.value?.id)) editor.value = false }
</script>
<template>
  <section class="workspace business-theme"><div class="page-heading"><div><span class="eyebrow">AIRSPACE SAFETY</span><h1>空域安全管控</h1><p>配置区域 → 检查航线 → 起飞复核 → 保存记录</p></div><el-button :disabled="busy" @click="refresh">刷新区域与记录</el-button></div><el-alert v-if="error" :title="error" type="error" :closable="false" /><el-alert v-if="notice" :title="notice" type="success" :closable="false" />
    <p class="scope-note">红色为禁飞区，橙色为限高区，灰色为停用/非生效时段；红线为当前检查的违规航段。判断使用业务高度，非无人机可视化抬升高度。本版检查起飞前规划路径，执行中的任务不自动改线。</p>
    <div class="map"><CityViewport :aircraft="sky.snapshot.aircraft" :stations="sky.snapshot.stations" :tasks="sky.snapshot.tasks" :zones="zones" :airspace-check="result" :focused-zone-id="focusedZoneId" /></div>
    <AirspaceCheckPanel :tasks="sky.snapshot.tasks" :result="result" :busy="busy" :can-operate="sky.canOperate" @check="check" />
    <AirspaceZoneTable :zones="zones" :busy="busy" :can-manage="canManage" @create="edit()" @edit="edit" @focus="focus" />
    <AirspaceCheckHistory :rows="checks" :busy="busy" @open="open" />
    <AirspaceZoneEditor v-if="editor" :zone="selected" :busy="busy" :server-error="error" @save="submit" @close="editor = false" />
  </section>
</template>
<style scoped>.workspace { padding:24px; min-height:100%; display:grid; gap:18px; }.workspace .page-heading { margin-bottom:0; }.scope-note { font-size:12px; color:#a1c1d3; line-height:1.8; margin:0; }.map { height:560px; min-height:400px; }</style>
