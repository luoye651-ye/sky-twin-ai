<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { aircraftTypes, type Aircraft } from '@sky/sky'
const props = defineProps<{ action: string; row: Record<string, any>; aircraft: Aircraft[]; busy: boolean; serverError?: string }>()
const emit = defineEmits<{ save: [data: { aircraftId: string; reason: string }]; close: [] }>()
const aircraftId = shallowRef('')
const reason = shallowRef('')
const labels: Record<string, string> = { assign: '分配飞行器', start: '执行仿真', cancel: '取消任务', fail: '标记失败', resolve: '处置事件' }
const candidates = computed(() => props.aircraft.filter(a => a.status === 'idle' && a.battery >= Math.max(25, (props.row.durationSeconds ?? 0) * 0.08 + 20) && a.payloadCapacity >= (props.row.payload ?? 0) && (props.row.type === 'commute' ? a.type === 'evtol' && a.seats >= props.row.passengers : props.row.type === 'logistics' ? a.type === 'cargo' : a.type !== 'evtol')))
const valid = computed(() => !!reason.value.trim() && (props.action !== 'assign' || !!aircraftId.value))
</script>
<template>
  <el-dialog :model-value="true" :title="labels[action]" width="540px" @close="emit('close')">
    <p>{{ row.title }}</p>
    <el-alert v-if="serverError" :title="serverError" type="error" :closable="false" />
    <el-form label-width="90px" @submit.prevent="valid && emit('save', { aircraftId, reason })">
      <el-form-item v-if="action === 'assign'" label="飞行器"><el-select v-model="aircraftId"><el-option v-for="a in candidates" :key="a.id" :value="a.id" :label="`${a.name} · ${aircraftTypes[a.type]} · ${a.battery.toFixed(0)}%`" /></el-select></el-form-item>
      <el-form-item label="操作原因" required><el-input v-model="reason" type="textarea" maxlength="500" placeholder="填写调度原因或处置结果，保存至操作记录" /></el-form-item>
    </el-form>
    <template #footer><el-button @click="emit('close')">取消</el-button><el-button type="primary" :disabled="!valid" :loading="busy" @click="emit('save', { aircraftId, reason })">确认{{ labels[action] }}</el-button></template>
  </el-dialog>
</template>
