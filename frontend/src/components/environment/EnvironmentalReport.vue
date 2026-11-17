<script setup lang="ts">
import { onUnmounted, shallowRef, watch } from 'vue'
import { getEnvironmentalReport } from '../../api/environment'
import type { EnvironmentalReport } from '@sky/environment'
const props = defineProps<{ reportId: string }>()
const report = shallowRef<EnvironmentalReport>(), error = shallowRef(''), showSnapshot = shallowRef(false)
let generation = 0, alive = true
watch(() => props.reportId, async id => { const token = ++generation; report.value = undefined; error.value = ''; try { const value = await getEnvironmentalReport(id); if (alive && token === generation) report.value = value } catch (e) { if (alive && token === generation) error.value = String(e) } }, { immediate: true })
function download() { if (!report.value) return; const url = URL.createObjectURL(new Blob([report.value.content], { type: 'text/plain;charset=utf-8' })), a = document.createElement('a'); a.href = url; a.download = `environment-${report.value.id}.txt`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000) }
onUnmounted(() => { alive = false; generation++ })
</script>
<template><section class="card"><h2>不可变归档报告</h2><p v-if="error">{{ error }}</p><template v-if="report"><p>{{ report.id }} · {{ report.createdBy }} · {{ report.createdTime }}</p><div class="actions"><el-button @click="download">下载环境处置报告</el-button><el-button @click="showSnapshot = !showSnapshot">{{ showSnapshot ? '隐藏' : '查看' }}证据快照</el-button></div><pre>{{ report.content }}</pre><pre v-if="showSnapshot">{{ JSON.stringify(report.snapshot, null, 2) }}</pre></template></section></template>
<style scoped>.card { padding:20px; border:1px solid #24465d; background:#0b2132; }.card h2 { font-size:17px; margin-top:0; }.card p { font-size:12px; color:#acc7d8; }.card pre { white-space:pre-wrap; overflow-wrap:anywhere; font-size:13px; line-height:1.9; max-height:600px; overflow:auto; color:#d7edf7; }.actions { display:flex; gap:12px; }</style>
