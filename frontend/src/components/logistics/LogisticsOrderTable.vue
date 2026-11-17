<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { LogisticsAction, LogisticsOrder } from '../../api/logistics'
import { statusLabels } from '@sky/sky'
import { deliveryStage, formatTime, isOverdue } from './logisticsPresentation'

const props = defineProps<{ orders: LogisticsOrder[]; loading: boolean; canOperate: boolean; busy: boolean }>()
const emit = defineEmits<{
  operate: [action: LogisticsAction, order: LogisticsOrder]
  detail: [order: LogisticsOrder]
}>()
const page = ref(1)
const rows = computed(() => props.orders.slice((page.value - 1) * 20, page.value * 20))
watch(() => props.orders.length, size => { if ((page.value - 1) * 20 >= size) page.value = 1 })
</script>

<template>
  <el-table v-loading="loading" :data="rows" row-key="id" stripe empty-text="暂无配送订单">
    <el-table-column prop="cargoName" label="货物" min-width="160" />
    <el-table-column prop="weight" label="重量 kg" width="95" />
    <el-table-column prop="startStationName" label="起点" min-width="140" show-overflow-tooltip />
    <el-table-column prop="endStationName" label="终点" min-width="140" show-overflow-tooltip />
    <el-table-column prop="aircraftName" label="执行飞行器" min-width="150"><template #default="{row}">{{ row.aircraftName || '尚未分配' }}</template></el-table-column>
    <el-table-column label="配送阶段" width="135"><template #default="{row}"><el-tag :type="row.status === 'delivered' ? 'success' : ['failed','cancelled'].includes(row.taskStatus) ? 'info' : 'primary'">{{ deliveryStage(row) }}</el-tag></template></el-table-column>
    <el-table-column label="任务状态" width="100"><template #default="{row}">{{ statusLabels[row.taskStatus] ?? row.taskStatus }}</template></el-table-column>
    <el-table-column label="任务进度" min-width="140"><template #default="{row}"><el-progress :percentage="Math.max(0,Math.min(100,Math.round(row.progress)))" /></template></el-table-column>
    <el-table-column label="截止时间" min-width="195"><template #default="{row}">{{ formatTime(row.deadlineAt) }}<br><el-tag v-if="isOverdue(row)" type="warning" size="small">超过配送时限</el-tag></template></el-table-column>
    <el-table-column label="操作" width="370" fixed="right">
      <template #default="{row}">
        <el-button link type="primary" @click="emit('detail',row)">查看配送</el-button>
        <RouterLink :to="{ path: '/digital-twin', query: { taskId: row.taskId } }" class="map-track-link">地图跟踪</RouterLink>
        <template v-if="canOperate && row.status === 'created'">
          <el-button v-if="row.taskStatus === 'created'" link type="primary" :disabled="busy" @click="emit('operate','assign',row)">分配</el-button>
          <el-button v-if="row.taskStatus === 'assigned'" link type="primary" :disabled="busy" @click="emit('operate','start',row)">执行仿真</el-button>
          <el-button v-if="row.taskStatus === 'completed'" link type="success" :disabled="busy" @click="emit('operate','deliver',row)">确认送达</el-button>
          <el-button v-if="['created','assigned','executing'].includes(row.taskStatus)" link type="danger" :disabled="busy" @click="emit('operate','cancel',row)">取消配送</el-button>
        </template>
      </template>
    </el-table-column>
  </el-table>
  <el-pagination v-model:current-page="page" :page-size="20" :total="orders.length" layout="prev,pager,next,total" />
</template>

<style scoped>
.el-pagination { margin-top:16px; }
.map-track-link { color:#37cfff; font-size:14px; margin:0 12px; text-decoration:none; }
</style>
