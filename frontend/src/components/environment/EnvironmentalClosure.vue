<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import type { DiscoveryDetail } from '@sky/environment'
const props = defineProps<{ detail: DiscoveryDetail; disabled: boolean }>()
defineEmits<{ close: [resolution: string, image: File] }>()
const resolution = shallowRef(''), image = shallowRef<File>(), error = shallowRef('')
const canClose = computed(() => props.detail.status === 'in_response' && props.detail.responses[props.detail.responses.length - 1]?.taskStatus === 'completed' && props.detail.responses.every(r => !['created', 'assigned', 'executing'].includes(r.taskStatus)))
function choose(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]; error.value = ''; image.value = undefined
  if (file && (file.size > 2 * 1024 * 1024 || !['image/png', 'image/jpeg'].includes(file.type))) error.value = '请选择2MiB以内的PNG或JPEG'
  else image.value = file
}
</script>
<template><section v-if="detail.status === 'in_response'" class="card"><h2>4 · 提交处置后证据并归档</h2><p>先完成最新应急侦察；若失败或取消，请重新安排。图片与说明由人工提供，不证明现实中已清理。结案时Java还会核对事件点上空的实际仿真轨迹。</p><div class="fields"><label>人工处置说明<textarea v-model="resolution" aria-label="环境处置说明" maxlength="500" :disabled="disabled || !canClose" placeholder="记录线下处置方式、结果及仿真性质"></textarea></label><label>处置后图片<input type="file" aria-label="处置后图片" accept="image/png,image/jpeg" :disabled="disabled || !canClose" @change="choose"></label><el-button type="primary" :disabled="disabled || !canClose || !resolution.trim() || !image" @click="image && $emit('close', resolution, image)">提交证据并结案归档</el-button></div><p v-if="!canClose">等待最新侦察任务完成，暂不能结案。</p><p v-if="error" class="error">{{ error }}</p></section></template>
<style scoped>.card { padding:20px; border:1px solid #24465d; background:#0b2132; }.card h2 { font-size:17px; margin-top:0; }.card p { font-size:12px; color:#a1bed0; line-height:1.8; }.fields { display:flex; align-items:end; gap:16px; flex-wrap:wrap; }.fields label { display:grid; gap:8px; font-size:13px; color:#acc7d8; }.fields textarea { width:400px; max-width:100%; height:90px; background:#102a3d; color:#e1f1fa; border:1px solid #31546b; padding:10px; }.error { color:#ff9f8d!important; }</style>
