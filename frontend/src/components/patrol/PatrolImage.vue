<script setup lang="ts">
import { onUnmounted, shallowRef, watch } from 'vue'
import { getPatrolImage } from '../../api/patrol'
import type { PatrolRow } from '@sky/patrol'
const props = defineProps<{ runId: string; item: PatrolRow }>()
const emit = defineEmits<{ close: [] }>()
const open = shallowRef(true), url = shallowRef(''), loading = shallowRef(false), error = shallowRef('')
watch(() => [props.runId, props.item.id] as const, async ([run, id], _old, cleanup) => {
  let stale = false
  cleanup(() => { stale = true })
  if (url.value) URL.revokeObjectURL(url.value)
  url.value = ''; error.value = ''; loading.value = true
  try {
    const blob = await getPatrolImage(run, id, 'predicted')
    if (!stale) url.value = URL.createObjectURL(blob)
  } catch (e) {
    if (!stale) error.value = e instanceof Error ? e.message : '图片读取失败'
  } finally { if (!stale) loading.value = false }
}, { immediate: true })
onUnmounted(() => { if (url.value) URL.revokeObjectURL(url.value) })
</script>

<template>
  <el-dialog v-model="open" aria-label="检测图片预览" width="min(1100px, 94vw)"
    top="5vh" append-to-body destroy-on-close class="patrol-image-dialog" @closed="emit('close')">
    <p v-if="loading" role="status">正在加载检测图…</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <img v-if="url" :src="url" :alt="`检测图 ${item.filename}`" class="detection-image" />
  </el-dialog>
</template>

<style scoped>
.detection-image { display:block; width:100%; height:auto; max-height:75vh; object-fit:contain; background:#04101a; }
</style>
