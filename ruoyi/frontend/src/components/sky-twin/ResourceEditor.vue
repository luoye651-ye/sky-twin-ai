<script setup lang="ts">
import { reactive, shallowRef } from 'vue'
import { aircraftTypes, stationTypes } from '@sky/sky'
const props = defineProps<{ kind: 'aircraft' | 'stations'; row?: Record<string, any>; busy: boolean; serverError?: string }>()
const emit = defineEmits<{ save: [data: Record<string, any>]; close: [] }>()
const defaults = props.kind === 'aircraft'
  ? { name: '', type: 'drone', model: '', longitude: 121.4737, latitude: 31.2304, battery: 100, payloadCapacity: 2, seats: 0 }
  : { name: '', type: 'takeoff', longitude: 121.4737, latitude: 31.2304, status: 'enabled' }
const form = reactive({ ...defaults, ...props.row })
const error = shallowRef('')
function save() {
  if (!form.name?.trim() || (props.kind === 'aircraft' && !form.model?.trim())) { error.value = '请填写名称和型号'; return }
  if (form.type === 'evtol' && (form.seats ?? 0) < 1) { error.value = 'eVTOL 至少需要一个座位'; return }
  emit('save', { ...form, seats: props.kind === 'aircraft' && form.type !== 'evtol' ? 0 : form.seats })
}
</script>
<template>
  <el-dialog :model-value="true" :title="row ? '编辑资源' : '新增资源'" width="600px" @close="emit('close')">
    <el-alert v-if="error || serverError" :title="serverError || error" type="error" :closable="false" />
    <el-form label-width="100px" @submit.prevent="save">
      <el-form-item label="名称" required><el-input v-model="form.name" maxlength="80" /></el-form-item>
      <el-form-item label="类型" required><el-select v-model="form.type"><el-option v-for="(label, value) in (kind === 'aircraft' ? aircraftTypes : stationTypes)" :key="value" :label="label" :value="value" /></el-select></el-form-item>
      <el-form-item v-if="kind === 'aircraft'" label="型号" required><el-input v-model="form.model" maxlength="80" /></el-form-item>
      <el-form-item label="经度 / 纬度"><el-input-number v-model="form.longitude" :min="-180" :max="180" :precision="6" :step="0.001" /><el-input-number v-model="form.latitude" :min="-90" :max="90" :precision="6" :step="0.001" /></el-form-item>
      <template v-if="kind === 'aircraft'">
        <el-form-item label="电量 %"><el-input-number v-model="form.battery" :min="0" :max="100" /></el-form-item>
        <el-form-item label="载重 kg"><el-input-number v-model="form.payloadCapacity" :min="0" :max="10000" /></el-form-item>
        <el-form-item v-if="form.type === 'evtol'" label="座位数"><el-input-number v-model="form.seats" :min="1" :max="20" /></el-form-item>
      </template>
      <el-form-item v-else label="状态"><el-select v-model="form.status"><el-option label="启用" value="enabled" /><el-option label="停用" value="disabled" /></el-select></el-form-item>
    </el-form>
    <template #footer><el-button @click="emit('close')">取消</el-button><el-button type="primary" :loading="busy" @click="save">保存</el-button></template>
  </el-dialog>
</template>
