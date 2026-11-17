<script setup lang="ts">
import { shallowRef } from 'vue'
import { useSkyStore } from '../../stores/sky'
import { statusLabels } from '../../../../shared/sky'
import TaskActionDialog from '../../../../ruoyi/frontend/src/components/sky-twin/TaskActionDialog.vue'
const sky = useSkyStore()
const selected = shallowRef<Record<string, any>>()
const busy = shallowRef(false)
const error = shallowRef('')
async function resolve(data: Record<string, any>) {
  busy.value = true
  try { await sky.operate(`/events/${selected.value!.id}/resolve`, data); selected.value = undefined }
  catch (e) { error.value = e instanceof Error ? e.message : '处置失败' }
  finally { busy.value = false }
}
</script>
<template><section class="events-panel"><h2>异常事件与处置</h2><el-alert v-if="error" :title="error" type="error" @close="error = ''" /><article v-for="event in sky.snapshot.events" :key="event.id" class="event-card"><div><el-tag :type="event.severity === 'high' ? 'danger' : 'warning'">{{ event.severity === 'high' ? '高' : event.severity === 'low' ? '低' : '中' }}</el-tag><strong>{{ event.title }}</strong><p>{{ event.aircraftId || '未分配飞行器' }} · {{ event.createdTime }} · {{ statusLabels[event.status] }}</p><p v-if="event.resolution">{{ event.resolvedBy }}：{{ event.resolution }}</p></div><RouterLink v-if="event.discoveryId" :to="{ path: '/environment', query: { discoveryId: event.discoveryId } }">进入环境闭环处置 →</RouterLink><el-button v-else-if="sky.canOperate && event.status === 'open'" type="warning" plain @click="selected = event">处置</el-button></article><p v-if="!sky.snapshot.events.length" class="empty-note">暂无异常；任务告警和人工确认的环境发现会生成事件。</p><TaskActionDialog v-if="selected" action="resolve" :row="selected" :aircraft="sky.snapshot.aircraft" :busy="busy" :server-error="error" @save="resolve" @close="selected = undefined" /></section></template>
<style scoped>
.events-panel { padding: 24px; }.event-card { display: flex; justify-content: space-between; gap: 16px; align-items: center; border: 1px solid #5d4831; background: #221e1a; padding: 20px; margin-top: 14px; }.event-card strong { margin-left: 12px; }.event-card p { color: #bea98d; font-size: 12px; line-height: 1.7; }
</style>
