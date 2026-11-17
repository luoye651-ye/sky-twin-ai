<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import type { EvidenceBox, VisionAnalysis } from '@sky/environment'
import { analyzeEvidence } from '../../api/environment'
const props = defineProps<{ file?: File; disabled: boolean }>()
const emit = defineEmits<{ result: [analysis: VisionAnalysis | undefined, boxes: EvidenceBox[]]; pending: [value: boolean] }>()
const analysis = shallowRef<VisionAnalysis>(), error = shallowRef(''), busy = shallowRef(false)
const selected = shallowRef<number[]>([])
let sequence = 0
watch(() => props.file, (_file, _old, cleanup) => {
  sequence++; analysis.value = undefined; selected.value = []; error.value = ''; busy.value = false
  emit('pending', false); emit('result', undefined, [])
  cleanup(() => { sequence++ })
})
const predictions = computed(() => analysis.value?.result?.predictions ?? [])
function publish() {
  emit('result', analysis.value, predictions.value.filter((_p, i) => selected.value.includes(i)).slice(0, 20).map(p => ({
    x: p.x, y: p.y, width: p.width, height: p.height, note: `${p.label} 模型置信度${p.confidence.toFixed(3)}，待人工复核`,
  })))
}
function toggle(index: number, checked: boolean) {
  selected.value = checked ? [...selected.value, index].slice(0, 20) : selected.value.filter(i => i !== index)
  publish()
}
async function analyze() {
  if (!props.file || busy.value || props.disabled) return
  const ticket = ++sequence; busy.value = true; error.value = ''; analysis.value = undefined; selected.value = []
  emit('result', undefined, []); emit('pending', true)
  try {
    const value = await analyzeEvidence(props.file, crypto.randomUUID())
    if (ticket !== sequence) return
    analysis.value = value
    if (value.status !== 'completed') throw new Error(value.errorMessage || '本次分析未完成，请稍后重新分析')
    selected.value = (value.result?.predictions ?? []).slice(0, 20).map((_p, i) => i); publish()
  } catch (e) { if (ticket === sequence) error.value = e instanceof Error ? e.message : '分析失败' }
  finally { if (ticket === sequence) { busy.value = false; emit('pending', false) } }
}
</script>
<template>
  <section class="vision-analysis" aria-label="上传影像AI分析">
    <el-button :disabled="!file || disabled || busy" :loading="busy" @click="analyze">{{ busy ? '模型分析中…' : '分析这张图片' }}</el-button>
    <p>使用已发布漂浮物模型；结果仅供复核。位置、拍摄来源和采集时间需由你确认。</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <template v-if="analysis?.status === 'completed'">
      <p>分析 {{ analysis.id }} · 模型 {{ analysis.modelName }} · 检出 {{ predictions.length }} 个（最多选择20个）。置信度不代表识别准确率。</p>
      <label v-for="(p, i) in predictions" :key="i" class="prediction"><input type="checkbox" :checked="selected.includes(i)" :disabled="disabled || busy || (!selected.includes(i) && selected.length >= 20)" @change="toggle(i, ($event.target as HTMLInputElement).checked)">{{ p.label }} · 置信度 {{ p.confidence.toFixed(3) }}</label>
      <p v-if="!predictions.length">未检出目标，不代表没有漂浮物。可在下方人工补框，保留本次分析记录。</p>
      <el-button :disabled="disabled || busy" @click="selected = []; publish()">改用下方人工框</el-button>
    </template>
  </section>
</template>
<style scoped>.vision-analysis{margin:12px 0;padding:14px;border:1px solid #31546b}.vision-analysis p{font-size:12px;color:#acc7d8;overflow-wrap:anywhere}.prediction{display:inline-flex;align-items:center;gap:6px;margin:5px 12px 5px 0;font-size:12px;color:#d4e9f4}.prediction input{width:auto}</style>
