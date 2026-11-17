<script setup lang="ts">
import { shallowRef } from 'vue'
import { ElMessage } from 'element-plus'
import { useSkyStore } from '../../stores/sky'
import { javaRequest } from '../../api/sky'
import BusinessTable from '../../../../ruoyi/frontend/src/components/sky-twin/BusinessTable.vue'
import TaskEditor from '../../../../ruoyi/frontend/src/components/sky-twin/TaskEditor.vue'
import TaskActionDialog from '../../../../ruoyi/frontend/src/components/sky-twin/TaskActionDialog.vue'
const sky = useSkyStore()
const editor = shallowRef(false)
const busy = shallowRef(false)
const action = shallowRef('')
const selected = shallowRef<Record<string, any>>()
const detail = shallowRef('')
const error = shallowRef('')
async function save(data: Record<string, any>) {
  busy.value = true
  try { await sky.operate(action.value ? `/tasks/${selected.value!.id}/${action.value}` : '/tasks', data); editor.value = false; ElMessage.success('任务操作已保存') }
  catch (e) { error.value = e instanceof Error ? e.message : '操作失败' }
  finally { busy.value = false }
}
async function handleAction(name: string, row: Record<string, any>) {
  selected.value = row
  if (name === 'tracks') {
    try { const points = (await javaRequest(`/sky/tasks/${row.id}/tracks`)).data; detail.value = points.length ? JSON.stringify(points, null, 2) : '任务尚未执行，暂无轨迹。' }
    catch (e) { error.value = e instanceof Error ? e.message : '轨迹查询失败' }
  } else { action.value = name; editor.value = true }
}
function create() { selected.value = undefined; action.value = ''; editor.value = true }
</script>
<template>
  <section class="workbench business-theme">
    <div class="page-heading"><div><span class="eyebrow">MISSION CENTER</span><h1>统一任务管理</h1><p>创建 → 分配 → 空域复核 → 执行 → 服务端确认完成</p><RouterLink to="/airspace">前往空域管控检查航线 →</RouterLink></div><el-button v-if="sky.canOperate" type="primary" @click="create">创建仿真任务</el-button></div>
    <el-alert v-if="error" :title="error" type="error" @close="error = ''" />
    <RouterLink to="/route-planning">规划多航点绕行航线 →</RouterLink>
    <BusinessTable kind="tasks" :rows="sky.snapshot.tasks" :loading="sky.loading" :can-manage="false" :can-operate="sky.canOperate" @action="handleAction" />
    <TaskEditor v-if="editor && !action" :stations="sky.snapshot.stations" :busy="busy" :server-error="error" @save="save" @close="editor = false" />
    <TaskActionDialog v-if="editor && action" :action="action" :row="selected!" :aircraft="sky.snapshot.aircraft" :busy="busy" :server-error="error" @save="save" @close="editor = false" />
    <el-dialog :model-value="!!detail" title="持久化飞行轨迹" width="75%" @close="detail = ''"><pre class="record-detail">{{ detail }}</pre></el-dialog>
  </section>
</template>
<style scoped>
.workbench { padding: 24px; min-height: 100%; }.record-detail { white-space: pre-wrap; max-height: 60vh; overflow: auto; }
</style>
