import { onMounted, onUnmounted, shallowRef, watch } from 'vue'
import { getPatrolConfig, getPatrolRun, getPatrolRuns, startPatrol } from '../api/patrol'
import type { PatrolConfig, PatrolRun } from '@sky/patrol'
export function usePatrolEvaluation(initialId = '') {
  const config = shallowRef<PatrolConfig>({ ready: false, message: '正在读取模型配置…' })
  const history = shallowRef<PatrolRun[]>([]), detail = shallowRef<PatrolRun>(), selectedId = shallowRef(initialId)
  const busy = shallowRef(false), error = shallowRef(''), notice = shallowRef('')
  let alive = true, generation = 0, refreshing = false, pendingRequest: string | undefined, timer: ReturnType<typeof setTimeout> | undefined
  async function load() {
    const id = selectedId.value, ticket = ++generation
    detail.value = undefined
    if (!id) return
    try { const value = await getPatrolRun(id); if (alive && ticket === generation) detail.value = value }
    catch (e) { if (alive && ticket === generation) error.value = e instanceof Error ? e.message : '读取评测失败' }
  }
  async function refresh() {
    if (refreshing) return
    refreshing = true
    const ticket = generation, id = selectedId.value
    try {
      const [cfg, rows] = await Promise.all([getPatrolConfig(), getPatrolRuns()])
      if (!alive) return
      config.value = cfg; history.value = rows
      if (!selectedId.value && rows[0]) selectedId.value = (rows.find(row => ['queued', 'running'].includes(row.status)) ?? rows[0]).id
      else if (id) { const value = await getPatrolRun(id); if (alive && ticket === generation && selectedId.value === id) detail.value = value }
    } catch (e) { if (alive) error.value = e instanceof Error ? e.message : '后台连接失败' }
    finally { refreshing = false }
  }
  async function poll() { await refresh(); if (alive) timer = setTimeout(poll, 1800) }
  async function start() {
    if (busy.value) return
    busy.value = true; error.value = ''; notice.value = ''
    pendingRequest ??= crypto.randomUUID()
    try {
      const value = await startPatrol(pendingRequest)
      pendingRequest = undefined
      if (!alive) return
      notice.value = value.reused ? '已有评测记录，已恢复查看；未重复启动GPU任务' : '仿真巡逻已启动，后台正在对HAIDA test进行真实模型评测'
      if (selectedId.value === value.id) detail.value = value
      else selectedId.value = value.id
      await refresh()
    } catch (e) { if (alive) error.value = e instanceof Error ? e.message : '启动失败；再次点击会复用提交标识，避免重复任务' }
    finally { if (alive) busy.value = false }
  }
  watch(selectedId, load, { immediate: true })
  onMounted(poll)
  onUnmounted(() => { alive = false; generation++; clearTimeout(timer) })
  return { config, history, detail, selectedId, busy, error, notice, refresh, start }
}
