<script setup lang="ts">
import { computed, reactive, shallowRef } from 'vue'
import { taskTypes, stationTypes, type Station } from '@sky/sky'
const props = defineProps<{ stations: Station[]; busy: boolean; serverError?: string }>()
const emit = defineEmits<{ save: [data: Record<string, any>]; close: [] }>()
const form = reactive({ title: '', type: 'environment', startStationId: '', endStationId: '', payload: 0, passengers: 0, speed: 10, cruiseAltitude: 60, reason: '' })
const eligibleStations = computed(() => props.stations.filter(station => station.status === 'enabled' && (form.type !== 'commute' || station.type === 'vertiport')))
const error = shallowRef('')
function changeType() {
  form.startStationId = ''; form.endStationId = ''
  form.passengers = form.type === 'commute' ? 1 : 0
  error.value = ''
}
function save() {
  if (!form.title.trim() || !form.reason.trim() || !form.startStationId || !form.endStationId) { error.value = '请填写任务名、起终站点和创建原因'; return }
  emit('save', { ...form, passengers: form.type === 'commute' ? form.passengers : 0 })
}
</script>
<template>
  <el-dialog :model-value="true" title="创建仿真任务" width="620px" @close="emit('close')">
    <el-alert title="本地仿真 · 10倍演示时间 · 不发送实机飞行指令" type="info" :closable="false" />
    <el-alert v-if="error || serverError" :title="serverError || error" type="error" :closable="false" />
    <el-form label-width="110px" @submit.prevent="save">
      <el-form-item label="任务名称" required><el-input v-model="form.title" maxlength="100" /></el-form-item>
      <el-form-item label="任务类型"><el-select v-model="form.type" @change="changeType"><el-option v-for="(label, value) in taskTypes" :key="value" :label="label" :value="value" /></el-select></el-form-item>
      <el-form-item label="起点站点" required><el-select v-model="form.startStationId" filterable><el-option v-for="s in eligibleStations" :key="s.id" :value="s.id" :label="`${s.name} · ${stationTypes[s.type]}`" /></el-select></el-form-item>
      <el-form-item label="终点站点" required><el-select v-model="form.endStationId" filterable><el-option v-for="s in eligibleStations" :key="s.id" :value="s.id" :label="s.name" :disabled="s.id === form.startStationId" /></el-select></el-form-item>
      <el-form-item label="载荷 kg"><el-input-number v-model="form.payload" :min="0" :max="10000" /></el-form-item>
      <el-form-item v-if="form.type === 'commute'" label="乘客数"><el-input-number v-model="form.passengers" :min="1" :max="20" /></el-form-item>
      <el-form-item label="巡航速度 m/s"><el-input-number v-model="form.speed" :min="1" :max="50" /></el-form-item>
      <el-form-item label="巡航高度 m"><el-input-number v-model="form.cruiseAltitude" :min="20" :max="120" /></el-form-item>
      <el-form-item label="创建原因" required><el-input v-model="form.reason" type="textarea" maxlength="500" /></el-form-item>
    </el-form>
    <template #footer><el-button @click="emit('close')">取消</el-button><el-button type="primary" :loading="busy" @click="save">创建任务</el-button></template>
  </el-dialog>
</template>
