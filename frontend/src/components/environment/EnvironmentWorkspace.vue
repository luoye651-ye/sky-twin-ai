<script setup lang="ts">
import { computed, nextTick, shallowRef, useTemplateRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSkyStore } from '../../stores/sky'
import { useEnvironment } from '../../composables/useEnvironment'
import { discoveryStatuses } from '@sky/environment'
import type { RouteSketch } from '@sky/routes'
import CityViewport from '../business/CityViewport.vue'
import DiscoveryForm from './DiscoveryForm.vue'
import DiscoveryReview from './DiscoveryReview.vue'
import EnvironmentalResponse from './EnvironmentalResponse.vue'
import EnvironmentalClosure from './EnvironmentalClosure.vue'
import EnvironmentalReport from './EnvironmentalReport.vue'
const props = withDefaults(defineProps<{ responseMode?: boolean }>(), { responseMode: false })
const sky = useSkyStore(), route = useRoute(), router = useRouter(), env = useEnvironment(() => sky.refresh(), typeof route.query.discoveryId === 'string' ? route.query.discoveryId : '')
const { rows, detail, selectedId, filter, busy, error, notice } = env
const viewport = useTemplateRef<InstanceType<typeof CityViewport>>('viewport'), marked = shallowRef(false)
const visible = computed(() => props.responseMode ? rows.value.filter(r => !['pending_review', 'rejected'].includes(r.status)) : rows.value)
const sketch = computed<RouteSketch | undefined>(() => detail.value && marked.value ? { points: [{ longitude: detail.value.longitude, latitude: detail.value.latitude, altitude: 0 }, { longitude: detail.value.longitude, latitude: detail.value.latitude, altitude: 0 }], waypoints: [{ longitude: detail.value.longitude, latitude: detail.value.latitude }], altitude: 0, selected: -1 } : undefined)
async function focus() { if (!detail.value) return; marked.value = true; await nextTick(); viewport.value?.focusPosition(detail.value.longitude, detail.value.latitude, 0) }
watch(visible, list => { if (!selectedId.value && list[0]) selectedId.value = list[0].id })
watch(selectedId, id => { marked.value = false; if (id && route.query.discoveryId !== id) void router.replace({ query: { ...route.query, discoveryId: id } }) })
watch(() => route.query.discoveryId, id => { if (typeof id === 'string') selectedId.value = id })
</script>
<template><section class="workspace business-theme"><div class="page-heading"><div><span class="eyebrow">ENVIRONMENT TO RESPONSE · EVIDENCE WORKFLOW</span><h1>{{ responseMode ? '环境事件应急处置' : '环境发现 → 应急处置闭环' }}</h1><p>影像上传 / 人工标注 → 人工复核 → 事件 → 应急侦察 → 处置后证据 → 不可变归档</p></div><RouterLink :to="responseMode ? '/environment' : '/emergency-process'">{{ responseMode ? '环境巡逻 →' : '应急事件总览 →' }}</RouterLink></div><el-alert title="本页保存人工证据与处置记录；AI巡逻识别请进入环境发现。影像来源和位置为用户声明，飞行为本地仿真，不代表真实清理或救援。" type="warning" :closable="false" /><el-alert v-if="error" :title="error" type="error" :closable="false" /><el-alert v-if="notice" :title="notice" type="success" :closable="false" />
  <DiscoveryForm v-if="!responseMode" :tasks="sky.snapshot.tasks" :disabled="busy || !sky.canOperate" :submit="env.create" />
  <section class="selector"><div class="toolbar"><h2>发现记录（最近200条）</h2><select v-model="filter" aria-label="环境发现状态筛选" :disabled="busy"><option value="">全部状态</option><option v-for="(label, value) in discoveryStatuses" :key="value" :value="value">{{ label }}</option></select><el-button :disabled="busy" @click="env.refresh">刷新环境闭环</el-button><RouterLink to="/task-management">创建 / 执行巡检任务 →</RouterLink></div><div class="rows"><button v-for="r in visible" :key="r.id" :class="{ selected: selectedId === r.id }" :disabled="busy" :aria-label="`查看发现${r.title}`" @click="selectedId = r.id">{{ r.title }} · {{ discoveryStatuses[r.status] }} · {{ r.createdTime }}</button><p v-if="!visible.length">暂无此状态记录。</p></div></section>
  <template v-if="detail"><DiscoveryReview :key="detail.id" :detail="detail" :disabled="busy || !sky.canOperate" @review="env.review" @focus="focus" /><div class="map"><CityViewport ref="viewport" :aircraft="sky.snapshot.aircraft" :stations="sky.snapshot.stations" :tasks="sky.snapshot.tasks" :zones="sky.snapshot.airspaceZones" :route-sketch="sketch" /><span v-if="marked" class="map-note">黄色标记：用户标注的发现点，不是图片自动地理定位</span></div><EnvironmentalResponse :key="`response-${detail.id}`" :detail="detail" :stations="sky.snapshot.stations" :aircraft="sky.snapshot.aircraft" :tasks="sky.snapshot.tasks" :disabled="busy || !sky.canOperate" @respond="env.respond" @task-action="env.taskAction" /><EnvironmentalClosure :key="`closure-${detail.id}`" :detail="detail" :disabled="busy || !sky.canOperate" @close="env.close" /><EnvironmentalReport v-if="detail.report" :report-id="detail.report.id" /><section class="audit"><h2>闭环审计</h2><p v-for="a in detail.audit" :key="a.id">{{ a.createdTime }} · {{ a.actor }} · {{ a.action }} · {{ a.reason }}</p></section></template>
  <RouterLink to="/environment">返回环境巡逻 →</RouterLink>
</section></template>
<style scoped>.workspace { padding:24px; display:grid; gap:18px; }.page-heading { margin-bottom:0; }.selector,.audit { padding:20px; border:1px solid #24465d; background:#0b2132; }.selector h2,.audit h2 { font-size:17px; margin:0; }.toolbar { display:flex; flex-wrap:wrap; gap:14px; align-items:center; }.toolbar select { background:#102a3d; color:#e1f1fa; border:1px solid #31546b; padding:9px; }.toolbar a { color:#76cfeb; font-size:13px; }.rows { display:grid; gap:10px; max-height:230px; overflow:auto; margin-top:16px; }.rows button { padding:12px; background:#102a3d; color:#bad6e7; border:1px solid #31546b; text-align:left; cursor:pointer; }.rows .selected { border-color:#5fdcff; color:#ecfbff; }.rows p,.audit p { color:#acc7d8; font-size:12px; line-height:1.8; }.map { height:480px; position:relative; }.map-note { position:absolute; left:20px; bottom:65px; padding:10px; color:#ffdc66; background:#071b2bea; font-size:12px; }</style>
