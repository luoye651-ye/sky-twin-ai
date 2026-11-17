<script setup lang="ts">
import { computed, reactive, shallowRef, watch } from 'vue'
import { useSkyStore } from '../../stores/sky'
import { useOperationPage } from '../../composables/useOperationPage'
import { opsWrite, type OpsRow } from '../../api/operations'
import OperationsTable from './OperationsTable.vue'
import StationCapacityPanel from './StationCapacityPanel.vue'
const sky = useSkyStore(), form = reactive({ aircraftId: '', kind: 'charging', reason: '' }), requestId = shallowRef(crypto.randomUUID() as string)
const manage = computed(() => sky.permissions.includes('*:*:*') || sky.permissions.includes('sky:manage'))
const { rows, page, total, busy, error, notice, act } = useOperationPage(() => '/resources')
const closing = shallowRef<OpsRow>(), resolution = shallowRef(''), battery = shallowRef(100)
watch(form, () => { requestId.value = crypto.randomUUID() })
async function start() { if (!form.reason.trim() || !form.aircraftId) return; await act(async () => { await opsWrite('/resources', { ...form, requestId: requestId.value }); requestId.value = crypto.randomUUID(); await sky.refresh().catch(() => {}) }) }
async function close() { if (!closing.value || !resolution.value.trim()) return; const id = String(closing.value.id); await act(async () => { await opsWrite(`/resources/${encodeURIComponent(id)}/close`, { reason: resolution.value, battery: battery.value }); closing.value = undefined; await sky.refresh().catch(() => {}) }) }
</script>
<template><section><h2>资源运维</h2><p>充电/维护期间禁止派机；故障停用会将正在占用该飞机的任务标为失败。这里记录仿真资源状态，不远程控制真实设备。</p><el-alert v-if="error" :title="error" type="error" :closable="false" /><el-alert v-if="notice" :title="notice" type="success" :closable="false" />
  <form class="fields" @submit.prevent="start"><el-select v-model="form.aircraftId" placeholder="选择飞机" aria-label="运维飞机"><el-option v-for="a in sky.snapshot.aircraft" :key="a.id" :label="`${a.name} · ${a.status}`" :value="a.id" /></el-select><el-select v-model="form.kind" aria-label="运维类型"><el-option label="仿真充电" value="charging" /><el-option label="维护停用" value="maintenance" /><el-option label="故障停用（占用任务将失败）" value="fault" /></el-select><el-input v-model="form.reason" maxlength="500" placeholder="操作原因" aria-label="运维原因" /><el-button native-type="submit" :disabled="busy || !manage || !form.reason.trim() || !form.aircraftId">开始运维</el-button></form>
  <OperationsTable :rows="rows" :total="total" :page="page" :busy="busy" :columns="[{key:'aircraftName',label:'飞机'},{key:'kind',label:'类型'},{key:'status',label:'状态'},{key:'reason',label:'原因'},{key:'resolution',label:'结束说明'}]" @page="page = $event"><template #actions="{ row }"><el-button v-if="row.status === 'active'" :disabled="busy || !manage" @click="closing = row; resolution = ''">结束并恢复可用</el-button></template></OperationsTable>
  <el-dialog :model-value="!!closing" title="结束运维" :close-on-click-modal="!busy" :show-close="!busy" @close="closing = undefined"><el-input v-model="resolution" maxlength="500" placeholder="处理结果与恢复原因" aria-label="运维结束说明" /><label v-if="closing?.kind === 'charging'">充电后仿真电量<el-input-number v-model="battery" :min="0" :max="100" /></label><p>维护和故障恢复保留原电量；充电值不能低于原电量。</p><el-button :disabled="busy || !resolution.trim()" @click="close">确认恢复可用</el-button></el-dialog>
  <StationCapacityPanel />
</section></template>
<style scoped>.fields{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}.fields :deep(.el-select){width:260px}.fields :deep(.el-input){max-width:280px}</style>
