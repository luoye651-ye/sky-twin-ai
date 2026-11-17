<script setup lang="ts">
import { shallowRef } from 'vue'
import type { Report } from '../../../../shared/sky'
defineProps<{ reports: Report[] }>()
const selected = shallowRef<Report>()
</script>
<template><section class="records-panel"><h2>任务报告</h2><p class="empty-note">系统根据仿真轨迹与任务结果生成摘要；影像 AI 分析后续接入。</p><article v-for="report in reports" :key="report.id" class="record-card"><div><strong>{{ report.title }}</strong><p>{{ report.createdTime }} · {{ report.createdBy }}</p></div><el-button type="primary" plain @click="selected = report">查看报告</el-button></article><p v-if="!reports.length" class="empty-note">任务完成或终止后自动生成报告。</p><el-dialog :model-value="!!selected" title="任务报告" width="680px" @close="selected = undefined"><pre class="report-content">{{ selected?.content }}</pre></el-dialog></section></template>
<style scoped>
.records-panel { padding: 24px; }.record-card { display: flex; justify-content: space-between; gap: 16px; align-items: center; padding: 20px; border: 1px solid #22445c; background: #0a1e2d; margin-top: 14px; }.record-card p { color: #84a6bd; font-size: 12px; }.report-content { white-space: pre-wrap; line-height: 1.9; }
</style>
