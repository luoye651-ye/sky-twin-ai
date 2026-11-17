<script setup lang="ts">
import { statusLabels } from '@sky/sky'
import { valueText, type OpsRow } from '../../api/operations'
defineProps<{ rows: OpsRow[]; columns: { key: string; label: string }[]; busy: boolean; total: number; page: number }>()
defineEmits<{ page: [value: number]; select: [row: OpsRow] }>()
const extraLabels: Record<string,string> = { active: '进行中', closed: '已结束', scheduled: '已排班', reviewed: '已审核', draft: '草稿' }
function cell(row: OpsRow, key: string) { const value = valueText(row, key); return ['status', 'taskStatus', 'kind'].includes(key) ? statusLabels[value] ?? (extraLabels[value] ?? value) : value }
</script>
<template>
  <el-table :data="rows" row-key="id" v-loading="busy" @row-click="$emit('select', $event)">
    <el-table-column v-for="column in columns" :key="column.key" :label="column.label" min-width="125"><template #default="{ row }">{{ cell(row, column.key) }}</template></el-table-column>
    <el-table-column label="操作" min-width="260"><template #default="{ row }"><slot name="actions" :row="row" /></template></el-table-column>
  </el-table>
  <el-pagination :current-page="page" :page-size="20" :total="total" layout="prev,pager,next,total" :disabled="busy" @current-change="$emit('page', $event)" />
</template>
