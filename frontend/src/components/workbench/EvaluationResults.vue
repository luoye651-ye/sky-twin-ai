<script setup lang="ts">
import { computed } from 'vue'
import type { EvaluationRow } from '../../types/workbench'
const props = defineProps<{ rows: EvaluationRow[] }>()
const summaries = computed(() => [...new Set(props.rows.map(r => r.variant))].map(variant => {
  const rows = props.rows.filter(r => r.variant === variant), times = rows.map(r => r.latency_ms).sort((a,b) => a-b)
  return { variant, total: rows.length, passed: rows.filter(r => r.passed).length, p95: times[Math.max(0,Math.ceil(times.length*.95)-1)] ?? 0 }
}))
</script>
<template><section><h3>对照结果（规则断言，非事实正确率）</h3><p v-for="s in summaries" :key="s.variant">{{ s.variant }}：{{ s.passed }}/{{ s.total }} 通过断言 · P95 {{ s.p95 }}ms（小样本，仅本次记录）</p><details v-for="row in rows" :key="`${row.id}-${row.variant}`"><summary>{{ row.id }} · {{ row.variant }} · {{ row.passed ? '断言通过' : '未通过/失败' }} · {{ row.latency_ms }}ms</summary><p v-if="row.error" role="alert">{{ row.error }}</p><pre>{{ JSON.stringify(row, null, 2) }}</pre></details></section></template>
<style scoped>pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:500px;overflow:auto;font:13px/1.8 sans-serif}details{padding:10px 0;border-bottom:1px solid #31546b}p{font-size:13px;color:#9ebfd2}</style>
