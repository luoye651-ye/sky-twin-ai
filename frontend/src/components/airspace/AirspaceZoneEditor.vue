<script setup lang="ts">
import { reactive, shallowRef } from 'vue'
import type { AirspaceZone, AirspaceZoneInput } from '@sky/airspace'
const props = defineProps<{ zone?: AirspaceZone; busy: boolean; serverError?: string }>()
const emit = defineEmits<{ save: [input: AirspaceZoneInput]; close: [] }>()
const form = reactive<AirspaceZoneInput>(props.zone ? { ...props.zone, enabled: !!props.zone.enabled, reason: '' } : {
  name: '', type: 'no_fly', west: 120.188, south: 30.193, east: 120.192, north: 30.197,
  minAltitude: 0, maxAltitude: 120, startsAt: null, endsAt: null, enabled: true, reason: '',
})
const localError = shallowRef('')
function submit() {
  localError.value = ''
  if (!form.name.trim() || !form.reason.trim()) { localError.value = '请填写区域名称和操作原因'; return }
  if (!(form.west < form.east && form.south < form.north)) { localError.value = '西经度须小于东经度，南纬度须小于北纬度'; return }
  if (form.minAltitude > form.maxAltitude) { localError.value = '高度下限不能大于上限'; return }
  emit('save', { ...form, minAltitude: form.type === 'height_limit' ? 0 : form.minAltitude, name: form.name.trim(), reason: form.reason.trim(), startsAt: form.startsAt || null, endsAt: form.endsAt || null })
}
function beforeClose(done: () => void) { if (!props.busy) done() }
</script>
<template>
  <el-dialog :model-value="true" :title="zone ? '编辑空域区域' : '新建空域区域'" width="min(650px, 95vw)" :before-close="beforeClose" :close-on-click-modal="!busy" :close-on-press-escape="!busy" :show-close="!busy" @close="$emit('close')">
    <el-alert v-if="localError" :title="localError" type="error" :closable="false" />
    <el-alert v-if="serverError" :title="serverError" type="error" :closable="false" />
    <el-form label-width="100px" :disabled="busy" @submit.prevent="submit">
      <el-form-item label="区域名称"><el-input v-model="form.name" maxlength="80" aria-label="区域名称" /></el-form-item>
      <el-form-item label="区域类型"><el-select v-model="form.type" aria-label="区域类型"><el-option label="禁飞区" value="no_fly" /><el-option label="限高区" value="height_limit" /></el-select></el-form-item>
      <div class="coordinates"><el-form-item label="西经度"><el-input-number v-model="form.west" :precision="6" :min="-180" :max="180" :step=".001" aria-label="西经度" /></el-form-item><el-form-item label="东经度"><el-input-number v-model="form.east" :precision="6" :min="-180" :max="180" :step=".001" aria-label="东经度" /></el-form-item><el-form-item label="南纬度"><el-input-number v-model="form.south" :precision="6" :min="-90" :max="90" :step=".001" aria-label="南纬度" /></el-form-item><el-form-item label="北纬度"><el-input-number v-model="form.north" :precision="6" :min="-90" :max="90" :step=".001" aria-label="北纬度" /></el-form-item></div>
      <el-form-item v-if="form.type === 'no_fly'" label="高度下限 m"><el-input-number v-model="form.minAltitude" :min="0" :max="1000" aria-label="高度下限" /></el-form-item>
      <el-form-item :label="form.type === 'no_fly' ? '高度上限 m' : '允许最高 m'"><el-input-number v-model="form.maxAltitude" :min="0" :max="1000" aria-label="高度上限" /></el-form-item>
      <el-form-item label="开始生效"><el-date-picker v-model="form.startsAt" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" placeholder="留空表示立即/无起始限制" aria-label="开始生效时间" /></el-form-item>
      <el-form-item label="停止生效"><el-date-picker v-model="form.endsAt" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" placeholder="留空表示长期有效" aria-label="停止生效时间" /></el-form-item>
      <el-form-item label="启用"><el-switch v-model="form.enabled" aria-label="启用区域" /></el-form-item>
      <el-form-item label="操作原因"><el-input v-model="form.reason" type="textarea" maxlength="500" :rows="2" aria-label="区域操作原因" /></el-form-item>
      <p class="hint">第一版使用 WGS84 矩形，坐标为东经/北纬数值。高度为仿真原点相对高度；禁飞边界包含边线，限高允许等于上限，时间为开始包含、结束不包含。</p>
    </el-form>
    <template #footer><el-button :disabled="busy" @click="$emit('close')">取消</el-button><el-button type="primary" :loading="busy" @click="submit">保存区域</el-button></template>
  </el-dialog>
</template>
<style scoped>.coordinates { display:grid; grid-template-columns:1fr 1fr; }.hint { font-size:12px; color:#69849a; line-height:1.7; }@media(max-width:600px){.coordinates {grid-template-columns:1fr;}}</style>
