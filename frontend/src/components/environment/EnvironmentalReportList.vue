<script setup lang="ts">
import { onMounted, onUnmounted, shallowRef } from 'vue'
import { getEnvironmentalReports } from '../../api/environment'
import type { EnvironmentalReportSummary } from '@sky/environment'
import EnvironmentalReport from './EnvironmentalReport.vue'
const reports = shallowRef<EnvironmentalReportSummary[]>([]), selected = shallowRef(''), error = shallowRef('')
let alive = true
async function load() { try { const rows = await getEnvironmentalReports(); if (alive) reports.value = rows } catch (e) { if (alive) error.value = String(e) } }
onMounted(load); onUnmounted(() => { alive = false })
</script>
<template><section class="list"><h2>环境发现 → 应急处置归档</h2><p>人工证据与仿真任务的闭环报告；与普通飞行摘要分开保存。</p><el-button @click="load">刷新环境归档</el-button><p v-if="error">{{ error }}</p><article v-for="r in reports" :key="r.id"><strong>{{ r.title }}</strong><span>{{ r.createdTime }}</span><el-button @click="selected = r.id">查看环境归档报告</el-button><RouterLink :to="{ path: '/environment', query: { discoveryId: r.discoveryId } }">追溯发现与处置 →</RouterLink></article><p v-if="!reports.length">暂无已结案的环境报告。</p><EnvironmentalReport v-if="selected" :report-id="selected" /></section></template>
<style scoped>.list { padding:24px; }.list h2 { font-size:19px; }.list p,.list span { color:#acc7d8; font-size:12px; }.list article { display:flex; flex-wrap:wrap; gap:16px; align-items:center; padding:18px; background:#0b2132; border:1px solid #24465d; margin:14px 0; }.list a { color:#76cfeb; font-size:13px; }</style>
