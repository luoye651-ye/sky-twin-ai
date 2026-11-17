<script setup lang="ts">
import { shallowRef, watch } from 'vue'
import { getSkyToken, javaRequest } from '../../api/sky'
import type { VisionAnalysis } from '@sky/environment'
const props = defineProps<{ analysisId: string }>()
const emit = defineEmits<{ ask: [question: string] }>()
const detail = shallowRef<VisionAnalysis>(), url = shallowRef(''), error = shallowRef('')
watch(() => props.analysisId, async (id, _old, cleanup) => {
  const controller = new AbortController(); let alive = true, created = ''
  cleanup(() => { alive = false; controller.abort(); if (created) URL.revokeObjectURL(created) })
  detail.value = undefined; url.value = ''; error.value = ''
  try {
    const data = await javaRequest(`/sky/environment/analyses/${encodeURIComponent(id)}`, 'GET', undefined, controller.signal)
    const response = await fetch(`/java-api/sky/environment/analyses/${encodeURIComponent(id)}/image`, { signal: controller.signal, headers: { Authorization: `Bearer ${getSkyToken()}` } })
    if (!response.ok || !response.headers.get('Content-Type')?.startsWith('image/')) throw new Error('分析图片读取失败或无权限')
    const blob = await response.blob(); if (!alive) return
    created = URL.createObjectURL(blob); url.value = created; detail.value = data.data as VisionAnalysis
  } catch (e) { if (alive) error.value = e instanceof Error ? e.message : '图片读取失败' }
}, { immediate: true })
</script>
<template><section class="image-panel"><h3>图像分析 {{ analysisId }}</h3><p v-if="error" role="alert">{{ error }}</p><div v-if="url" class="evidence"><img :src="url" alt="所选分析原图"><button v-for="(box, i) in detail?.result?.predictions" :key="i" :style="{left:`${box.x*100}%`,top:`${box.y*100}%`,width:`${box.width*100}%`,height:`${box.height*100}%`}" :aria-label="`追问第${i+1}个预测框`" @click="emit('ask', `请读取所选分析证据，解释第${i+1}个预测框的标签、置信度和局限，说明需要哪些人工复核信息；不要推断拍摄地点。`)"><span>{{ i+1 }} · {{ box.label }} {{ (box.confidence*100).toFixed(1) }}%</span></button></div><p>点击预测框可带入追问。置信度不是识别准确率；AI回答基于结构化预测，不是再次看图。</p><small>模型 {{ detail?.modelName }} · {{ detail?.modelSha256 }}</small></section></template>
<style scoped>.image-panel{padding:12px;border:1px solid #31546b;margin:12px 0}.evidence{position:relative;display:table;max-width:600px;line-height:0}.evidence img{display:block;max-width:100%;image-orientation:none}.evidence button{position:absolute;box-sizing:border-box;border:2px solid #ffd067;background:transparent;cursor:pointer;min-width:8px;min-height:8px;color:#fff;padding:0}.evidence span{position:absolute;left:0;top:0;line-height:1.3;background:#102537dd;font-size:11px;white-space:nowrap}.image-panel small{overflow-wrap:anywhere}</style>
