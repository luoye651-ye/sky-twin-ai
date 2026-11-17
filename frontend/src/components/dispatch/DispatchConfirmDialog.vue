<script setup lang="ts">
import { shallowRef, watch } from 'vue'
const props = defineProps<{ open: boolean; busy: boolean; count: number; canConfirm: boolean }>()
const emit = defineEmits<{ close: []; confirm: [reason: string] }>()
const reason = shallowRef('')
watch(() => props.open, value => { if (value) reason.value = '' })
function beforeClose(done: () => void) { if (!props.busy) done() }
function confirm() { if (props.canConfirm && reason.value.trim() && !props.busy) emit('confirm', reason.value.trim()) }
</script>
<template>
  <el-dialog :model-value="open" title="确认本批派机" width="min(480px, 94vw)" :close-on-click-modal="!busy" :close-on-press-escape="!busy" :show-close="!busy" :before-close="beforeClose" @close="$emit('close')">
    <p>将为 {{ count }} 个任务分配飞行器，随后可在任务管理执行仿真。</p>
    <el-input v-model="reason" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="填写本次派机原因" aria-label="本批派机原因" :disabled="busy" />
    <template #footer><el-button :disabled="busy" @click="$emit('close')">取消</el-button><el-button type="primary" :loading="busy" :disabled="!reason.trim() || !canConfirm" @click="confirm">提交派机</el-button></template>
  </el-dialog>
</template>
