<script setup lang="ts">
import { computed, onUnmounted, reactive, shallowRef, watch } from 'vue'
import type { Task } from '@sky/sky'
import VisionAnalysisPanel from './VisionAnalysisPanel.vue'
import type { EvidenceBox, VisionAnalysis } from '@sky/environment'
import type { DiscoveryInput } from '@sky/environment'
const props = defineProps<{ tasks: Task[]; disabled: boolean; submit: (input: DiscoveryInput, file: File) => Promise<boolean> }>()
const form = reactive({ taskId: '', title: '河道漂浮物待复核', longitude: 120.19, latitude: 30.215, observedAt: new Date().toISOString(), imageSource: 'simulation' as 'simulation' | 'user_upload', x: .2, y: .2, width: .5, height: .5, note: '疑似漂浮物，需人工复核' })
const analysis = shallowRef<VisionAnalysis>(), modelBoxes = shallowRef<EvidenceBox[]>([]), analyzing = shallowRef(false)
function acceptAnalysis(value: VisionAnalysis | undefined, boxes: EvidenceBox[]) { analysis.value = value; modelBoxes.value = boxes; requestId.value = crypto.randomUUID() }
const boxes = computed<EvidenceBox[]>(() => modelBoxes.value.length ? modelBoxes.value : [{ x: form.x, y: form.y, width: form.width, height: form.height, note: form.note }])
const requestId = shallowRef(crypto.randomUUID()), image = shallowRef<File>(), preview = shallowRef(''), error = shallowRef('')
watch(form, () => { requestId.value = crypto.randomUUID() })
const patrols = computed(() => props.tasks.filter(t => t.type === 'environment' && ['executing', 'completed'].includes(t.status)))
const valid = computed(() => !!image.value && !!form.taskId && !!form.title.trim() && !!form.observedAt.trim())
function choose(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]; error.value = ''
  if (preview.value) URL.revokeObjectURL(preview.value)
  preview.value = ''; image.value = undefined; requestId.value = crypto.randomUUID()
  if (file && (file.size > 2 * 1024 * 1024 || !['image/png', 'image/jpeg'].includes(file.type))) { error.value = '请选择2MiB以内的PNG或JPEG'; return }
  if (file) { image.value = file; preview.value = URL.createObjectURL(file) }
}
async function save() {
  if (!image.value || !valid.value || props.disabled || analyzing.value) return
  error.value = ''
  const input: DiscoveryInput = { requestId: requestId.value, taskId: form.taskId, title: form.title, longitude: form.longitude, latitude: form.latitude, observedAt: form.observedAt, imageSource: form.imageSource, annotations: boxes.value, ...(analysis.value?.status === 'completed' ? { analysisId: analysis.value.id } : {}) }
  await props.submit(input, image.value)
}
onUnmounted(() => { if (preview.value) URL.revokeObjectURL(preview.value) })
</script>
<template><section class="card"><h2>1 · 提交河道漂浮物发现</h2><p>可先运行AI检测并选择候选框，再人工复核；也可直接人工标注。坐标由用户填写，不从单张图片推算真实地理位置；首次请先完成一个环境巡检任务。</p><form @submit.prevent="save"><fieldset :disabled="disabled || analyzing"><div class="fields"><label>关联巡检任务<select v-model="form.taskId" aria-label="关联巡检任务" required><option value="">请选择执行中/已完成巡检</option><option v-for="t in patrols" :key="t.id" :value="t.id">{{ t.title }}</option></select></label><label>发现标题<input v-model="form.title" aria-label="发现标题" maxlength="80" required></label><label>用户声明影像来源<select v-model="form.imageSource" aria-label="影像来源"><option value="simulation">仿真/示例图片</option><option value="user_upload">用户上传实拍资料（未验证来源）</option></select></label><label>经度 WGS84<input v-model.number="form.longitude" aria-label="发现经度" type="number" step="any" min="-180" max="180" required></label><label>纬度 WGS84<input v-model.number="form.latitude" aria-label="发现纬度" type="number" step="any" min="-90" max="90" required></label><label>采集时间（含时区）<input v-model="form.observedAt" aria-label="发现采集时间" required placeholder="2026-10-19T09:00:00Z"></label><label>发现图片 PNG/JPEG ≤2MiB<input aria-label="发现图片" type="file" accept="image/png,image/jpeg" @change="choose"></label></div><VisionAnalysisPanel :file="image" :disabled="disabled" @result="acceptAnalysis" @pending="analyzing = $event" /><p>标注框为原图比例（0～1），默认框不是识别结果，请根据图片调整。</p><div class="fields"><label v-for="key in (['x', 'y', 'width', 'height'] as const)" :key="key">{{ key }}<input v-model.number="form[key]" :aria-label="`标注框${key}`" type="number" min="0" max="1" step="0.01" required></label><label>人工标注说明<input v-model="form.note" aria-label="人工标注说明" maxlength="200"></label></div><div v-if="preview" class="preview"><img :src="preview" alt="待提交影像预览"><span v-for="(box, index) in boxes" :key="index" :style="{ left: `${box.x * 100}%`, top: `${box.y * 100}%`, width: `${box.width * 100}%`, height: `${box.height * 100}%` }"></span></div><p v-if="error" class="error">{{ error }}</p><button class="primary" type="submit" :disabled="!valid">提交发现，等待人工复核</button></fieldset></form></section></template>
<style scoped>.card { padding:20px; border:1px solid #24465d; background:#0b2132; }.card h2 { font-size:17px; margin-top:0; }.card p { color:#a1bed0; font-size:12px; line-height:1.8; }fieldset { border:0; padding:0; min-width:0; }.fields { display:flex; gap:14px; flex-wrap:wrap; }.fields label { display:grid; gap:6px; color:#acc7d8; font-size:12px; margin-bottom:12px; }.fields input,.fields select { padding:9px; border:1px solid #31546b; background:#102a3d; color:#e1f1fa; width:220px; box-sizing:border-box; }.preview { max-width:500px; display:table; position:relative; margin:12px 0; line-height:0; }.preview img { image-orientation:none; display:block; max-width:100%; max-height:320px; }.preview span { position:absolute; box-sizing:border-box; border:2px solid #ffd067; pointer-events:none; }.primary { padding:10px 16px; background:#238fc7; color:white; border:0; cursor:pointer; }.primary:disabled { opacity:.4; cursor:default; }.error { color:#ff9f8d!important; }</style>
