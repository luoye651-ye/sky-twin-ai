<script setup lang="ts">
import { shallowRef, watch } from 'vue'
import { useSkyStore } from '../../stores/sky'
import { useOperationPage } from '../../composables/useOperationPage'
import { opsWrite, valueText, type OpsRow } from '../../api/operations'
import TaskOperationFilters from './TaskOperationFilters.vue'
import OperationsTable from './OperationsTable.vue'
const sky = useSkyStore(), keyword = shallowRef(''), state = shallowRef(''), type = shallowRef(''), query = shallowRef('')
const { rows, page, total, busy, error, notice, act, load } = useOperationPage(() => '/tasks' + query.value)
const retryRow = shallowRef<OpsRow>(), reason = shallowRef(''), deadline = shallowRef(120), requestId = shallowRef('')
function search() { const next = '?' + new URLSearchParams({ keyword: keyword.value, state: state.value, type: type.value }); if (page.value === 1 && query.value === next) void load(); else { page.value = 1; query.value = next } }
watch([reason, deadline], () => { if (!busy.value) requestId.value = crypto.randomUUID() })
function open(row: OpsRow) { retryRow.value = row; reason.value = ''; requestId.value = crypto.randomUUID() }
async function retry() {
  if (!retryRow.value || !reason.value.trim()) return
  const row = retryRow.value
  await act(async () => { const result = await opsWrite(`/tasks/${encodeURIComponent(valueText(row, 'id'))}/retry`, { requestId: requestId.value, reason: reason.value, deadlineMinutes: deadline.value }); notice.value = `已创建重试任务 ${result.taskId}`; retryRow.value = undefined; await sky.refresh().catch(() => {}) })
}
</script>
<template>
  <section><h2>任务运营</h2><p>按服务端全库分页查询。提醒只提示处理延迟；重试保留原记录，创建待分配的新任务，物流使用填写的新期限。</p>
    <TaskOperationFilters v-model:keyword="keyword" v-model:state="state" v-model:type="type" :busy="busy" @search="search" />
    <el-alert v-if="error" :title="error" type="error" :closable="false" /><el-alert v-if="notice" :title="notice" type="success" :closable="false" />
    <OperationsTable :rows="rows" :total="total" :page="page" :busy="busy" :columns="[{key:'title',label:'任务'},{key:'status',label:'状态'},{key:'reminder',label:'处理提醒'},{key:'sourceTaskId',label:'原任务'}]" @page="page = $event"><template #actions="{ row }"><RouterLink :to="{path:'/route-planning',query:{taskId:String(row.id)}}">航线</RouterLink> · <RouterLink :to="{path:'/agent-command',query:{taskId:String(row.id)}}">AI方案</RouterLink><el-button v-if="['failed','cancelled'].includes(String(row.status))" :disabled="busy || !sky.canOperate" @click="open(row)">创建重试任务</el-button></template></OperationsTable>
    <el-dialog :model-value="!!retryRow" title="新建重试任务" :close-on-click-modal="!busy" :show-close="!busy" @close="retryRow = undefined"><p>原任务及历史轨迹保留；关联环境事件使用原处置重试流程，通勤班次需另建班次。</p><el-input v-model="reason" aria-label="任务重试原因" maxlength="500" placeholder="重试原因" /><label>物流新期限（分钟）<el-input-number v-model="deadline" :min="1" :max="1440" /></label><template #footer><el-button :disabled="busy || !reason.trim()" @click="retry">创建</el-button></template></el-dialog>
  </section>
</template>
