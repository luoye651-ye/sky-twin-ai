<script setup lang="ts">
import { aircraftTypes, stationTypes, taskTypes, statusLabels } from '@sky/sky'
const props = defineProps<{ kind: string; rows: Record<string, any>[]; loading: boolean; canManage: boolean; canOperate: boolean }>()
const emit = defineEmits<{ action: [action: string, row: Record<string, any>] }>()
const labels: Record<string, string> = { id: '编号', name: '名称', model: '型号', longitude: '经度', latitude: '纬度', altitude: '高度 m', battery: '电量 %', payloadCapacity: '载重 kg', seats: '座位', status: '状态', speed: '速度 m/s', type: '类型', title: '标题', aircraftName: '飞行器', progress: '进度 %', createdBy: '创建人', createdTime: '创建时间', startStationName: '起点', endStationName: '终点', severity: '级别', aircraftId: '飞行器编号', resolution: '处置结果', resolvedBy: '处置人', taskId: '任务编号', entityId: '对象编号', action: '操作', actor: '操作人', reason: '原因' }
const columns: Record<string, string[]> = {
  aircraft: ['name', 'type', 'model', 'battery', 'payloadCapacity', 'seats', 'status', 'longitude', 'latitude', 'altitude', 'speed'],
  stations: ['name', 'type', 'longitude', 'latitude', 'status'],
  tasks: ['title', 'type', 'status', 'progress', 'aircraftName', 'startStationName', 'endStationName', 'createdBy', 'createdTime'],
  events: ['title', 'severity', 'status', 'aircraftId', 'resolution', 'resolvedBy', 'createdTime'],
  reports: ['title', 'taskId', 'createdBy', 'createdTime'], audit: ['entityId', 'action', 'actor', 'reason', 'createdTime']
}
function display(row: Record<string, any>, key: string) {
  if (key === 'type') {
    const types = props.kind === 'aircraft' ? aircraftTypes : props.kind === 'stations' ? stationTypes : taskTypes
    return (types as Record<string, string>)[row[key]] ?? row[key]
  }
  if (key === 'status') return statusLabels[row[key]] ?? row[key]
  if (typeof row[key] === 'number' && !['seats'].includes(key)) return row[key].toFixed(['latitude', 'longitude'].includes(key) ? 6 : 1)
  return row[key] ?? '—'
}
</script>
<template>
  <el-table v-loading="loading" :data="rows" row-key="id" stripe max-height="650" empty-text="暂无记录">
    <el-table-column v-for="key in columns[kind]" :key="key" :label="labels[key]" :min-width="['title', 'createdTime', 'reason'].includes(key) ? 180 : 115" show-overflow-tooltip>
      <template #default="{ row }">{{ display(row, key) }}</template>
    </el-table-column>
    <el-table-column v-if="kind !== 'audit'" label="操作" fixed="right" :width="kind === 'tasks' ? 260 : 160">
      <template #default="{ row }">
        <template v-if="['aircraft', 'stations'].includes(kind) && canManage"><el-button link type="primary" @click="emit('action', 'edit', row)">编辑</el-button><el-button link type="danger" @click="emit('action', 'remove', row)">移除</el-button></template>
        <template v-if="kind === 'tasks'">
          <el-button link type="primary" @click="emit('action', 'tracks', row)">轨迹</el-button>
          <template v-if="canOperate">
            <el-button v-if="row.status === 'created'" link type="primary" @click="emit('action', 'assign', row)">分配</el-button>
            <el-button v-if="row.status === 'assigned'" link type="primary" @click="emit('action', 'start', row)">执行</el-button>
            <template v-if="['created', 'assigned', 'executing'].includes(row.status)"><el-button link type="warning" @click="emit('action', 'cancel', row)">取消</el-button><el-button link type="danger" @click="emit('action', 'fail', row)">失败</el-button></template>
          </template>
        </template>
        <el-button v-if="kind === 'events' && canOperate && row.status === 'open'" link type="primary" @click="emit('action', 'resolve', row)">处置</el-button>
        <el-button v-if="kind === 'reports'" link type="primary" @click="emit('action', 'report', row)">查看报告</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>
