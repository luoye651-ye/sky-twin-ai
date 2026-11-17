<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import { useSkyStore } from '../../stores/sky'
import { useOperationPage } from '../../composables/useOperationPage'
import { opsRead, opsWrite, type OpsRow } from '../../api/operations'
import ReportEditor from './ReportEditor.vue'
import OperationsTable from './OperationsTable.vue'
const sky = useSkyStore(), sourceKind = shallowRef('task'), sourceId = shallowRef(''), requestId = shallowRef(crypto.randomUUID() as string)
const detail = shallowRef<OpsRow>(), history = shallowRef<OpsRow>()
const { rows, page, total, busy, error, notice, act } = useOperationPage(() => '/reports')
const versions = computed(() => (detail.value?.versions as OpsRow[] | undefined) ?? [])
watch([sourceKind, sourceId], () => { requestId.value = crypto.randomUUID() })
async function create() { if (!sourceId.value.trim()) return; await act(async () => { detail.value = await opsWrite('/reports', { requestId: requestId.value, sourceKind: sourceKind.value, sourceId: sourceId.value.trim() }) }) }
async function open(row: OpsRow) { await act(async () => { detail.value = await opsRead<OpsRow>(`/reports/${encodeURIComponent(String(row.id))}`); history.value = undefined }) }
async function save(input: unknown) { if (!detail.value) return; const id = String(detail.value.id); await act(async () => { detail.value = await opsWrite(`/reports/${id}`, input, 'PUT') }) }
async function version(revision: number) { if (!detail.value) return; const id = String(detail.value.id); await act(async () => { history.value = await opsRead<OpsRow>(`/reports/${id}/versions/${revision}`) }) }
</script>
<template><section><h2>报告中心</h2><p>为任务或环境发现创建可追溯证据快照，再编辑或生成AI草稿。原有任务摘要与不可变环境归档仍在<RouterLink to="/patrol-report">巡检报告</RouterLink>保留。</p><el-alert v-if="error" :title="error" type="error" :closable="false" /><el-alert v-if="notice" :title="notice" type="success" :closable="false" /><div class="fields"><el-select v-model="sourceKind" aria-label="报告来源类型"><el-option label="任务" value="task" /><el-option label="环境发现" value="discovery" /></el-select><el-input v-model="sourceId" maxlength="40" placeholder="来源任务或发现编号" aria-label="报告来源编号" /><el-button :disabled="busy || !sky.canOperate || !sourceId.trim()" @click="create">创建证据快照草稿</el-button></div>
  <OperationsTable :rows="rows" :total="total" :page="page" :busy="busy" :columns="[{key:'title',label:'报告'},{key:'status',label:'状态'},{key:'revision',label:'版本'},{key:'sourceId',label:'来源编号'}]" @page="page = $event"><template #actions="{ row }"><el-button :disabled="busy" @click="open(row)">查看 / 编辑 / 导出</el-button></template></OperationsTable>
  <ReportEditor v-if="detail" :key="String(detail.id)" :report="detail" :disabled="busy || !sky.canOperate" @save="save"><p>历史版本：</p><el-button v-for="v in versions" :key="Number(v.revision)" :disabled="busy" @click="version(Number(v.revision))">v{{ v.revision }}</el-button><pre v-if="history" class="history">{{ history.content }}</pre></ReportEditor>
</section></template>
<style scoped>.fields{display:flex;gap:12px;margin:16px 0}.fields :deep(.el-input){max-width:400px}.fields :deep(.el-select){width:160px}.history{white-space:pre-wrap;overflow-wrap:anywhere}</style>
