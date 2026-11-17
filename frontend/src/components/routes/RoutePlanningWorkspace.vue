<script setup lang="ts">
import { computed, shallowRef, useTemplateRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useSkyStore } from '../../stores/sky'
import { useRoutePlanning } from '../../composables/useRoutePlanning'
import { statusLabels } from '@sky/sky'
import CityViewport from '../business/CityViewport.vue'
import RouteWaypointEditor from './RouteWaypointEditor.vue'
import RouteValidationPanel from './RouteValidationPanel.vue'
const sky = useSkyStore(), route = useRoute()
const selectedId = shallowRef(typeof route.query.taskId === 'string' ? route.query.taskId : '')
const viewport = useTemplateRef<InstanceType<typeof CityViewport>>('viewport')
const r = useRoutePlanning(() => selectedId.value, () => sky.refresh())
const { detail, draft, result, historical, busy, error, notice, reason, selected, mode, sketch, dirty } = r
const canEdit = computed(() => sky.canOperate && r.editable.value && !historical.value && ['created', 'assigned'].includes(sky.snapshot.tasks.find(t => t.id === selectedId.value)?.status ?? ''))
watch(() => sky.snapshot.tasks, tasks => { if (!selectedId.value && tasks.length) selectedId.value = (tasks.find(t => ['created', 'assigned'].includes(t.status)) ?? tasks[0])!.id }, { immediate: true })
</script>
<template>
  <section class="workspace business-theme"><div class="page-heading"><div><span class="eyebrow">WAYPOINT ROUTE PLANNING · SIMULATION</span><h1>多航点航线规划</h1><p>人工绘制绕行航点 → Java逐段校验 → 保存版本 → 沿同一路线仿真执行</p></div><RouterLink to="/task-management">返回任务管理 →</RouterLink></div>
    <RouterLink to="/traffic">多机冲突预测 / 错峰起飞 →</RouterLink>
    <el-alert title="支持启用矩形禁飞/限高区的候选绕行建议，不含建筑/地形避障或实机避碰。多机起飞前解冲突请进入多机协同页；已预约任务须先取消预约再改线。" type="warning" :closable="false" /><el-alert v-if="error" :title="error" type="error" :closable="false" /><el-alert v-if="notice" :title="notice" type="success" :closable="false" />
    <div class="toolbar"><label>选择任务<select v-model="selectedId" aria-label="航线规划任务" :disabled="busy"><option disabled value="">请选择任务</option><option v-for="t in sky.snapshot.tasks" :key="t.id" :value="t.id">{{ t.title }} · {{ statusLabels[t.status] }}</option></select></label><el-button :disabled="!selectedId || busy" @click="r.load">重新加载保存版本（丢弃草稿）</el-button><el-button :disabled="!canEdit || busy" @click="r.suggest">生成候选绕行（不保存）</el-button><el-button :disabled="!sketch" @click="viewport?.focusRouteDraft()">定位整条航线</el-button><RouterLink to="/airspace">配置禁飞区/限高区 →</RouterLink></div>
    <p v-if="detail" class="scope-note">{{ detail.title }} · 读取时状态：{{ statusLabels[detail.status] }} · {{ historical ? `查看历史 v${historical.revision}（只读）` : detail.plan.revision === 0 ? '旧任务兼容直线（无历史路线快照）' : `当前保存 v${detail.plan.revision}` }}。终端定位启用的飞行器不可派机；规划不替代起飞复核。</p>
    <div class="map"><CityViewport ref="viewport" :aircraft="sky.snapshot.aircraft" :stations="sky.snapshot.stations" :tasks="sky.snapshot.tasks" :zones="sky.snapshot.airspaceZones" :airspace-check="result?.check" :route-sketch="sketch" :route-editing="canEdit && !busy && mode !== 'navigate'" @route-pick="r.pick" /><span class="map-state">{{ historical ? '历史版本 · 只读' : mode === 'add' && canEdit ? '单击巡航平面添加航点' : mode === 'move' && canEdit ? `单击移动航点 ${selected + 1}` : '浏览地图 · 黄色为规划草稿' }}</span></div>
    <RouteWaypointEditor :points="historical?.waypoints ?? draft" :selected="selected" :disabled="!canEdit || busy" :mode="mode" :reason="reason" @mode="mode = $event" @select="selected = $event" @update="r.update" @remove="r.remove" @reorder="r.reorder" @reason="reason = $event" @clear="r.replace([])" />
    <RouteValidationPanel :result="result" :current="historical ?? detail?.plan" :busy="busy" :can-edit="canEdit" :reason="reason" :dirty="dirty" @preview="r.evaluate(false)" @save="r.evaluate(true)" />
    <section v-if="detail?.versions.length" class="history"><h2>不可变航线版本</h2><el-button v-if="historical" @click="r.version()">返回当前草稿</el-button><table><thead><tr><th>版本</th><th>原因</th><th>操作人</th><th>保存时间</th><th>查看</th></tr></thead><tbody><tr v-for="v in detail.versions" :key="v.revision"><td>v{{ v.revision }}</td><td>{{ v.reason }}</td><td>{{ v.createdBy }}</td><td>{{ v.createdTime }}</td><td><el-button :disabled="busy" @click="r.version(v.revision)">查看版本 {{ v.revision }}</el-button></td></tr></tbody></table></section>
  </section>
</template>
<style scoped>.workspace { padding:24px; display:grid; gap:18px; min-height:100%; }.page-heading { margin-bottom:0; }.toolbar { display:flex; flex-wrap:wrap; gap:16px; align-items:end; }.toolbar label { display:grid; gap:8px; font-size:12px; color:#a6bfd0; }.toolbar select { background:#102a3d; color:#d8effa; border:1px solid #31546b; padding:9px; min-width:300px; max-width:650px; }.toolbar a { color:#70cdec; font-size:13px; }.scope-note { margin:0; color:#a6bfd0; font-size:12px; }.map { height:580px; position:relative; }.map-state { position:absolute; bottom:64px; right:18px; padding:10px; background:#071b2bed; color:#ffe28e; border:1px solid #a28039; pointer-events:none; font-size:12px; }.history { padding:18px; background:#0b1d2d; border:1px solid #21445b; overflow:auto; }.history h2 { margin:0 0 16px; font-size:16px; }.history table { width:100%; border-collapse:collapse; font-size:12px; }.history th,.history td { text-align:left; padding:10px; border-bottom:1px solid #21445b; }</style>
