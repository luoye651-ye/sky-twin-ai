<script setup lang="ts">
import { shallowRef } from 'vue'
import { skyRequest } from '@/api/sky'
import { useSkyWorkspace } from '@/composables/useSkyWorkspace'
import ResourceEditor from './ResourceEditor.vue'
import TaskEditor from './TaskEditor.vue'
import TaskActionDialog from './TaskActionDialog.vue'
import BusinessTable from './BusinessTable.vue'
const props = defineProps<{ kind: string; title: string }>()
const { snapshot, connected, error, loading, query, rows, canManage, canOperate, refresh, mutate, remove } = useSkyWorkspace(props.kind)
const editor = shallowRef(false)
const selected = shallowRef<Record<string, any>>()
const action = shallowRef('')
const busy = shallowRef(false)
const detail = shallowRef('')
async function save(data: Record<string, any>) {
  busy.value = true
  try {
    if (action.value) await mutate(`/${props.kind}/${selected.value!.id}/${action.value}`, 'post', data)
    else await mutate(`/${props.kind}${selected.value ? '/' + selected.value.id : ''}`, selected.value ? 'put' : 'post', data)
    editor.value = false; action.value = ''
  } catch (e) { error.value = e instanceof Error ? e.message : '保存失败' }
  finally { busy.value = false }
}
async function handleAction(name: string, row: Record<string, any>) {
  selected.value = row
  if (name === 'remove') { await remove(row); return }
  if (name === 'report') { detail.value = row.content; return }
  if (name === 'tracks') {
    try { const records = (await skyRequest(`/tasks/${row.id}/tracks`)).data; detail.value = records.length ? JSON.stringify(records, null, 2) : '该任务尚未执行，暂无轨迹。' }
    catch (e) { error.value = e instanceof Error ? e.message : '轨迹读取失败' }
    return
  }
  action.value = name === 'edit' ? '' : name; editor.value = true
}
function create() { selected.value = undefined; action.value = ''; editor.value = true }
</script>
<template>
  <div class="app-container">
    <div class="workspace-heading"><div><h2>{{ title }}</h2><p>独立仿真业务 · MySQL 持久化 · {{ connected ? '实时数据已连接' : '实时连接恢复中' }}</p></div><el-button @click="refresh">刷新</el-button></div>
    <el-alert v-if="error" :title="error" type="error" @close="error = ''" />
    <div class="workspace-toolbar"><el-input v-model="query" placeholder="搜索当前记录" clearable style="width: 300px" /><el-button v-if="(['aircraft', 'stations'].includes(kind) && canManage) || (kind === 'tasks' && canOperate)" type="primary" @click="create">{{ kind === 'tasks' ? '创建任务' : '新增资源' }}</el-button><el-tag type="info">最近500条</el-tag></div>
    <BusinessTable :kind="kind" :rows="rows" :loading="loading" :can-manage="canManage" :can-operate="canOperate" @action="handleAction" />
    <ResourceEditor v-if="editor && ['aircraft', 'stations'].includes(kind)" :kind="kind as 'aircraft' | 'stations'" :row="selected" :busy="busy" :server-error="error" @save="save" @close="editor = false" />
    <TaskEditor v-if="editor && kind === 'tasks' && !action" :stations="snapshot.stations" :busy="busy" :server-error="error" @save="save" @close="editor = false" />
    <TaskActionDialog v-if="editor && action" :action="action" :row="selected!" :aircraft="snapshot.aircraft" :busy="busy" :server-error="error" @save="save" @close="editor = false" />
    <el-dialog :model-value="!!detail" title="记录详情" width="75%" @close="detail = ''"><pre class="record-detail">{{ detail }}</pre></el-dialog>
  </div>
</template>
<style scoped>
.workspace-heading { display: flex; justify-content: space-between; align-items: center; }
.workspace-heading h2 { margin: 0 0 12px; }
.workspace-heading p { color: #64748b; }
.workspace-toolbar { display: flex; align-items: center; gap: 16px; margin: 20px 0; }
.record-detail { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.8; max-height: 65vh; overflow: auto; }
</style>
