<script setup lang="ts">
import { onScopeDispose, shallowRef, watch } from 'vue'
import { askAgent } from '../../api/agent'
import { exportOpsReport, valueText, type OpsRow } from '../../api/operations'
const props = defineProps<{ report: OpsRow; disabled: boolean }>()
const emit = defineEmits<{ save: [input: { expectedRevision: number; content: string; source: string; publish: boolean }] }>()
const content = shallowRef(''), ai = shallowRef(false), generating = shallowRef(false), error = shallowRef('')
let controller: AbortController | undefined, generation = 0
watch(() => [props.report.id, props.report.revision], () => { generation++; controller?.abort(); generating.value = false; content.value = valueText(props.report, 'content'); ai.value = props.report.source === 'ai_assisted'; error.value = '' }, { immediate: true })
async function generate() {
  if (generating.value || props.disabled) return
  const ticket = ++generation; controller = new AbortController(); const current = controller
  generating.value = true; error.value = ''; const timeout = setTimeout(() => current.abort(), 110000)
  let generatedText: string | undefined
  try { await askAgent(`请读取报告${props.report.id}的证据快照，起草一份500字以内的中文业务报告。仅陈述快照事实，区分仿真、人工声明和未知，不编造实机或清理结果，不保存、不审核。`, crypto.randomUUID(), current.signal, event => { if (generation === ticket && event.type === 'answer') { generatedText = event.data.text } }); if (generation === ticket && generatedText) { content.value = generatedText; ai.value = true } }
  catch (e) { if (generation === ticket) error.value = e instanceof Error ? e.message : 'AI草稿未完成，原文本保留' }
  finally { clearTimeout(timeout); if (generation === ticket) generating.value = false }
}
function save(publish: boolean) { if (!content.value.trim() || props.disabled || generating.value) return; emit('save', { expectedRevision: Number(props.report.revision), content: content.value, source: ai.value ? 'ai_assisted' : 'manual', publish }) }
async function download(format: 'txt' | 'html') { try { await exportOpsReport(String(props.report.id), format) } catch (e) { error.value = String(e) } }
onScopeDispose(() => { generation++; controller?.abort() })
</script>
<template><section><h3>{{ report.title }} · v{{ report.revision }} · {{ report.status }}</h3><p class="hash">来源 {{ report.sourceKind }} / {{ report.sourceId }} · 快照 SHA256 {{ report.snapshotSha256 }}</p><p>AI草稿需要外部模型调用并发送这份报告的证据，请核对资料范围后再点击；不会自动保存或审核。导出以已保存版本为准，HTML可在浏览器打印为PDF。</p><p v-if="error" role="alert">{{ error }}</p><el-button :disabled="disabled || report.status !== 'draft' || generating" @click="generate">生成AI报告草稿</el-button><el-button v-if="generating" @click="controller?.abort()">停止等待</el-button><el-button @click="download('txt')">导出TXT</el-button><el-button @click="download('html')">导出打印版HTML / PDF</el-button><el-input v-model="content" type="textarea" :rows="18" maxlength="20000" show-word-limit :disabled="disabled || report.status !== 'draft' || generating" aria-label="报告草稿正文" /><el-button :disabled="disabled || report.status !== 'draft' || generating || !content.trim()" @click="save(false)">保存新版本</el-button><el-button type="primary" :disabled="disabled || report.status !== 'draft' || generating || !content.trim()" @click="save(true)">审核并冻结</el-button><p>审核后不可修改。若业务证据在草稿期间变化，审核会被拒绝，需要重新创建快照。</p><slot /></section></template>
<style scoped>.hash{overflow-wrap:anywhere}</style>
