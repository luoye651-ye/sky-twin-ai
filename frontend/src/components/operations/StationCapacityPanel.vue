<script setup lang="ts">
import { onMounted, onScopeDispose, shallowRef } from 'vue'
import { useSkyStore } from '../../stores/sky'
import { opsRead, opsWrite, type OpsRow } from '../../api/operations'
const sky = useSkyStore(), rows = shallowRef<OpsRow[]>([]), error = shallowRef(''), busy = shallowRef(false), capacity = shallowRef(1), selected = shallowRef(''), reason = shallowRef('')
const manage = () => sky.permissions.includes('*:*:*') || sky.permissions.includes('sky:manage')
let alive = true
async function load() { try { const data = await opsRead<OpsRow[]>('/stations'); if (alive) rows.value = data } catch (e) { if (alive) error.value = String(e) } }
async function save() {
  if (busy.value || !selected.value || !reason.value.trim()) return
  busy.value = true; error.value = ''
  try { await opsWrite(`/stations/${encodeURIComponent(selected.value)}/capacity`, { capacity: capacity.value, reason: reason.value }, 'PUT'); await load() }
  catch (e) { if (alive) error.value = e instanceof Error ? e.message : '配置失败' }
  finally { if (alive) busy.value = false }
}
onMounted(load); onScopeDispose(() => { alive = false })
</script>
<template><section><h3>站点容量与占用</h3><p>未配置站点兼容原系统，默认200。配置后采用全航程保守占用，班次预约另按计划时间窗口核对；不是实机起降能力认证。</p><p v-if="error" role="alert">{{ error }}</p><el-table :data="rows"><el-table-column prop="name" label="站点" /><el-table-column prop="capacity" label="容量" /><el-table-column prop="occupied" label="当前仿真占用" /></el-table><form class="fields" @submit.prevent="save"><el-select v-model="selected" placeholder="选择站点" aria-label="容量配置站点"><el-option v-for="row in rows" :key="String(row.id)" :label="String(row.name)" :value="String(row.id)" /></el-select><el-input-number v-model="capacity" :min="1" :max="200" aria-label="站点容量" /><el-input v-model="reason" maxlength="500" placeholder="调整原因" /><el-button native-type="submit" :disabled="busy || !manage() || !reason.trim() || !selected">保存容量</el-button></form></section></template>
<style scoped>.fields{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}.fields :deep(.el-select){width:240px}.fields :deep(.el-input){max-width:280px}</style>
