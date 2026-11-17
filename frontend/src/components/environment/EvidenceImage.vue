<script setup lang="ts">
import { onUnmounted, shallowRef, watch } from 'vue'
import { getEvidenceImage } from '../../api/environment'
import type { EvidenceBox } from '@sky/environment'
const props = withDefaults(defineProps<{ discoveryId: string; after?: boolean; boxes?: EvidenceBox[] }>(), { after: false, boxes: () => [] })
const url = shallowRef(''), error = shallowRef(''), displayWidth = shallowRef(0)
function loaded(event: Event) { const img = event.target as HTMLImageElement; displayWidth.value = Math.min(img.naturalWidth, 650, 420 * img.naturalWidth / img.naturalHeight) }
let generation = 0, alive = true
watch(() => [props.discoveryId, props.after] as const, async ([id, after]) => {
  const token = ++generation; if (url.value) URL.revokeObjectURL(url.value); url.value = ''; error.value = ''; displayWidth.value = 0
  try { const blob = await getEvidenceImage(id, after); if (alive && token === generation) url.value = URL.createObjectURL(blob) }
  catch (e) { if (alive && token === generation) error.value = e instanceof Error ? e.message : '读取证据失败' }
}, { immediate: true })
onUnmounted(() => { alive = false; generation++; if (url.value) URL.revokeObjectURL(url.value) })
</script>
<template><div class="evidence"><div v-if="url" class="image-wrap" :style="{ width: displayWidth ? `${displayWidth}px` : undefined }"><img :src="url" :alt="after ? '人工提交的处置后证据' : '人工标注的发现证据'" @load="loaded"><span v-for="(b, i) in boxes" :key="i" class="box" :style="{ left: `${b.x * 100}%`, top: `${b.y * 100}%`, width: `${b.width * 100}%`, height: `${b.height * 100}%` }"><b>{{ i + 1 }} · 人工标注</b></span></div><p v-else>{{ error || '正在读取受权限保护的证据…' }}</p></div></template>
<style scoped>.evidence { max-width:650px; }.image-wrap { display:inline-block; position:relative; max-width:100%; line-height:0; }.image-wrap img { image-orientation:none; width:100%; height:auto; display:block; }.box { position:absolute; border:2px solid #ffd067; box-sizing:border-box; pointer-events:none; }.box b { position:absolute; top:0; left:0; color:#071b2b; background:#ffd067; font-size:11px; padding:5px; white-space:nowrap; line-height:1; }.evidence p { color:#acc7d8; font-size:12px; }</style>
