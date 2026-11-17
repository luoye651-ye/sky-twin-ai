<script setup lang="ts">
import type { AirspaceCheckRow } from '@sky/airspace'
defineProps<{ rows: AirspaceCheckRow[]; busy: boolean }>()
defineEmits<{ open: [id: string] }>()
const entries: Record<string, string> = { manual: '手动检查', start: '统一起飞', dispatch_confirm: '集群确认' }
</script>
<template><section class="panel business-theme"><h2>检查与拦截记录</h2><p class="hint">最近200条。检查通过表示当时校验通过，实际起飞结果以任务状态与审计为准。</p><el-table :data="rows" row-key="id"><el-table-column prop="createdTime" label="检查时间" min-width="180" /><el-table-column prop="taskTitle" label="任务" min-width="180" /><el-table-column label="入口" width="110"><template #default="{ row }">{{ entries[row.entry] || row.entry }}</template></el-table-column><el-table-column label="结果" width="90"><template #default="{ row }"><el-tag :type="row.allowed ? 'success' : 'danger'">{{ row.allowed ? '通过' : '拒绝' }}</el-tag></template></el-table-column><el-table-column prop="ruleRevision" label="规则版本" width="90" /><el-table-column prop="createdBy" label="操作人" width="95" /><el-table-column width="100"><template #default="{ row }"><el-button link type="primary" :disabled="busy" @click="$emit('open', row.id)">查看详情</el-button></template></el-table-column></el-table></section></template>
<style scoped>.panel { padding:18px; border:1px solid #24465d; border-radius:7px; background:#0b2132; }.panel h2 { margin:0; font-size:17px; }.hint { color:#92b4ca; font-size:12px; line-height:1.7; }</style>
