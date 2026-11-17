<script setup lang="ts">
import { useLogisticsDetail } from '../../composables/useLogisticsDetail'
import { deliveryStage, formatTime, isOverdue } from './logisticsPresentation'
import LogisticsTrackView from './LogisticsTrackView.vue'
const props = defineProps<{ orderId: string }>()
const emit = defineEmits<{ close: [] }>()
const { detail, tracks, loading, refreshing, error, trackError, refresh } = useLogisticsDetail(() => props.orderId)
const auditLabels: Record<string, string> = { 'order.create': '创建订单', 'order.deliver': '确认送达',
  'task.create': '创建任务', 'task.assign': '分配飞行器', 'task.start': '执行仿真', 'task.cancel': '取消任务',
  'task.complete': '仿真飞行完成', 'task.fail': '任务失败', 'event.low-battery': '低电量告警' }
</script>

<template>
  <el-dialog :model-value="true" title="配送详情与轨迹" width="min(1050px, 94vw)" @close="emit('close')">
    <div class="detail-toolbar"><span>状态和轨迹每3秒自动更新 · 仿真配送</span><el-button :loading="refreshing" @click="refresh()">刷新详情</el-button></div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <div v-loading="loading" class="detail-body">
      <template v-if="detail">
        <div class="detail-title"><h2>{{ detail.cargoName }}</h2><el-tag>{{ deliveryStage(detail) }}</el-tag><el-tag v-if="isOverdue(detail)" type="warning">航程超出配送时限</el-tag></div>
        <el-progress :percentage="Math.max(0, Math.min(100, Math.round(detail.progress)))" />
        <el-tabs>
          <el-tab-pane label="配送信息">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="订单编号">{{ detail.id }}</el-descriptions-item>
              <el-descriptions-item label="关联任务">{{ detail.taskId }}</el-descriptions-item>
              <el-descriptions-item label="起点">{{ detail.startStationName }}</el-descriptions-item>
              <el-descriptions-item label="终点">{{ detail.endStationName }}</el-descriptions-item>
              <el-descriptions-item label="货物重量">{{ detail.weight }} kg</el-descriptions-item>
              <el-descriptions-item label="执行飞行器">{{ detail.aircraftName || '尚未分配' }}</el-descriptions-item>
              <el-descriptions-item label="预计仿真耗时">{{ detail.durationSeconds }} 秒（10倍时间）</el-descriptions-item>
              <el-descriptions-item label="截止时间">{{ formatTime(detail.deadlineAt) }}</el-descriptions-item>
              <el-descriptions-item label="创建人">{{ detail.createdBy }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ formatTime(detail.createdTime) }}</el-descriptions-item>
              <el-descriptions-item label="送达确认人">{{ detail.deliveredBy || '尚未确认' }}</el-descriptions-item>
              <el-descriptions-item label="送达确认时间">{{ formatTime(detail.deliveredAt) }}</el-descriptions-item>
              <el-descriptions-item label="任务说明" :span="2">{{ detail.taskReason }}</el-descriptions-item>
            </el-descriptions>
            <p class="hint"><RouterLink :to="{path: '/route-planning', query: {taskId: detail.taskId}}" @click="emit('close')">查看/规划此配送任务的绕行航线 →</RouterLink></p>
            <p class="hint"><RouterLink :to="{path: '/digital-twin', query: {taskId: detail.taskId}}" @click="emit('close')">在数字孪生中跟踪位置、路线与剩余距离 →</RouterLink></p>
            <p class="hint">飞行器信息为当前资源状态；历史飞行位置和电量请查看轨迹记录。</p>
            <p v-if="detail.aircraftId" class="hint">当前电量 {{ detail.aircraftBattery?.toFixed(1) }}% · 高度 {{ detail.aircraftAltitude }} m · 位置 {{ detail.aircraftLongitude?.toFixed(6) }}, {{ detail.aircraftLatitude?.toFixed(6) }}</p>
          </el-tab-pane>
          <el-tab-pane label="飞行轨迹">
            <el-alert v-if="trackError" :title="trackError" type="error" :closable="false" />
            <LogisticsTrackView v-else :tracks="tracks" />
          </el-tab-pane>
          <el-tab-pane label="操作记录">
            <el-table :data="detail.audit" row-key="id" max-height="380">
              <el-table-column label="时间" min-width="180"><template #default="{row}">{{ formatTime(row.createdTime) }}</template></el-table-column>
              <el-table-column label="操作" min-width="140"><template #default="{row}">{{ auditLabels[row.action] || row.action }}</template></el-table-column>
              <el-table-column prop="actor" label="操作人" width="110" />
              <el-table-column prop="reason" label="原因" min-width="260" />
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </template>
    </div>
  </el-dialog>
</template>

<style scoped>
.detail-toolbar,.detail-title { display:flex; align-items:center; gap:12px; }.detail-toolbar { justify-content:space-between; color:#83a8bf; font-size:13px; margin-bottom:16px; }
.detail-body { min-height:180px; }.detail-title h2 { margin:0 0 12px; }.hint { color:#83a8bf; font-size:13px; line-height:1.7; }
</style>
