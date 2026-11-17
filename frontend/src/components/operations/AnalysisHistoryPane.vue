<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import { useSkyStore } from '../../stores/sky'
import { useOperationPage } from '../../composables/useOperationPage'
import { opsWrite, type OpsRow } from '../../api/operations'
import { javaRequest } from '../../api/sky'
import OperationsTable from './OperationsTable.vue'
const sky = useSkyStore(), filter = shallowRef(''), detail = shallowRef<OpsRow>()
const { rows, page, total, busy, error, notice, act, load } = useOperationPage(() => `/analyses?state=${filter.value}`)
async function select(row: OpsRow) { await act(async () => { detail.value = (await javaRequest(`/sky/environment/analyses/${encodeURIComponent(String(row.id))}`)).data }) }
const predictions = computed(() => (detail.value?.result as { predictions?: OpsRow[] } | null)?.predictions ?? [])
const retryRequests = new Map<string, string>()
async function retry(row: OpsRow) { const id = String(row.id); if (!retryRequests.has(id)) retryRequests.set(id, crypto.randomUUID()); await act(async () => { detail.value = await opsWrite(`/analyses/${encodeURIComponent(id)}/retry?requestId=${retryRequests.get(id)}`); retryRequests.delete(id) }) }
</script>
<template><section><h2>检测历史</h2><p>本地图片分析的历史记录、模型来源和关联发现；新上传请进入<RouterLink to="/environment?mode=evidence">上传检测</RouterLink>。离线影像巡逻仍保留原入口。</p><el-select v-model="filter" aria-label="分析状态" @change="page = 1"><el-option label="全部状态" value="" /><el-option label="已完成" value="completed" /><el-option label="失败" value="failed" /><el-option label="分析中" value="running" /></el-select><el-button :disabled="busy" @click="load">刷新</el-button><el-alert v-if="error" :title="error" type="error" :closable="false" /><el-alert v-if="notice" :title="notice" type="info" :closable="false" />
  <OperationsTable :rows="rows" :total="total" :page="page" :busy="busy" :columns="[{key:'id',label:'分析编号'},{key:'status',label:'状态'},{key:'modelName',label:'模型'},{key:'createdTime',label:'时间'},{key:'errorMessage',label:'失败原因'}]" @page="page = $event"><template #actions="{ row }"><el-button :disabled="busy" @click="select(row)">详情</el-button><RouterLink v-if="row.status === 'completed'" :to="{path:'/ai-workbench',query:{analysisId:String(row.id)}}">围绕图像追问</RouterLink><el-button v-if="row.status === 'failed' && row.createdBy === sky.username" :disabled="busy || !sky.canOperate" @click="retry(row)">重新分析</el-button><RouterLink v-if="row.discoveryId" :to="{path:'/environment',query:{discoveryId:String(row.discoveryId)}}">关联事件流程</RouterLink></template></OperationsTable>
  <el-dialog :model-value="!!detail" title="分析证据详情" width="min(850px,94vw)" @close="detail = undefined"><template v-if="detail"><p>分析 {{ detail.id }} · {{ detail.status }}</p><p class="hash">图片 SHA256：{{ detail.imageSha256 }}<br>模型 SHA256：{{ detail.modelSha256 }}</p><p>没有检出不等于没有目标；检测框置信度不代表准确率。</p><el-table :data="predictions"><el-table-column prop="label" label="类别" /><el-table-column prop="confidence" label="置信度" /><el-table-column v-for="key in ['x','y','width','height']" :key="key" :prop="key" :label="key" /></el-table></template></el-dialog>
</section></template>
<style scoped>.hash{overflow-wrap:anywhere}</style>
