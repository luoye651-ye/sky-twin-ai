import { onMounted, onUnmounted, shallowRef, watch } from 'vue'
import { closeDiscovery, createDiscovery, createEnvironmentalResponse, getDiscoveries, getDiscovery, reviewDiscovery } from '../api/environment'
import { javaRequest } from '../api/sky'
import type { DiscoveryDetail, DiscoveryInput, DiscoverySummary } from '@sky/environment'
export function useEnvironment(onChanged: () => Promise<void>, initialId = '') {
  const rows = shallowRef<DiscoverySummary[]>([]), detail = shallowRef<DiscoveryDetail>(), selectedId = shallowRef(initialId)
  const busy = shallowRef(false), error = shallowRef(''), notice = shallowRef(''), filter = shallowRef('')
  let alive = true, generation = 0, timer: ReturnType<typeof setTimeout> | undefined
  async function list() { const status = filter.value, value = await getDiscoveries(status || undefined); if (alive && status === filter.value) rows.value = value }
  async function load() {
    const id = selectedId.value, token = ++generation
    detail.value = undefined; error.value = ''
    if (!id) return
    try { const value = await getDiscovery(id); if (alive && token === generation) detail.value = value }
    catch (e) { if (alive && token === generation) error.value = e instanceof Error ? e.message : '发现详情读取失败' }
  }
  async function refresh() {
    const token = generation, id = selectedId.value
    try { await list(); if (id) { const value = await getDiscovery(id); if (alive && token === generation && id === selectedId.value) detail.value = value } }
    catch (e) { if (alive) error.value = e instanceof Error ? e.message : '刷新失败' }
  }
  async function poll() { if (!busy.value) await refresh(); if (alive) timer = setTimeout(poll, 4000) }
  async function action(work: () => Promise<DiscoveryDetail | void>, message: string) {
    if (busy.value) return false
    busy.value = true; error.value = ''; notice.value = ''; const token = ++generation
    try {
      const value = await work()
      if (!alive) return true
      notice.value = message
      if (value && token === generation) { if (selectedId.value === value.id) detail.value = value; else selectedId.value = value.id }
      try { await Promise.all([refresh(), onChanged()]) }
      catch { if (alive) error.value = '操作已保存，刷新任务列表失败，请手动刷新' }
      return true
    } catch (e) { if (alive) error.value = e instanceof Error ? e.message : '业务操作失败'; return false }
    finally { if (alive) busy.value = false }
  }
  const create = (input: DiscoveryInput, file: File) => action(() => createDiscovery(input, file), '发现已保存，等待人工复核；尚未生成事件')
  const review = (input: { decision: 'confirm' | 'reject'; severity: string; reason: string }) => selectedId.value ? action(() => reviewDiscovery(selectedId.value, input), input.decision === 'confirm' ? '复核已确认并生成环境事件' : '发现已驳回，未生成环境事件') : Promise.resolve(false)
  const respond = (input: { startStationId: string; endStationId: string; reason: string }) => selectedId.value ? action(() => createEnvironmentalResponse(selectedId.value, input), '应急侦察任务及事件上空航线已创建，请分配并执行或进入集群调度') : Promise.resolve(false)
  const close = (resolution: string, image: File) => selectedId.value ? action(() => closeDiscovery(selectedId.value, resolution, image), '事件、处置后证据和归档报告已一并保存') : Promise.resolve(false)
  const taskAction = (taskId: string, command: string, aircraftId: string, reason: string) => action(() => javaRequest(`/sky/tasks/${encodeURIComponent(taskId)}/${command}`, 'POST', { aircraftId: aircraftId || null, reason }).then(() => undefined), '任务操作已保存；飞行由Java推进')
  watch(selectedId, load, { immediate: true })
  watch(filter, refresh)
  onMounted(poll)
  onUnmounted(() => { alive = false; generation++; clearTimeout(timer) })
  return { rows, detail, selectedId, busy, error, notice, filter, refresh, create, review, respond, close, taskAction }
}
