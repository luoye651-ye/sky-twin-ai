import { computed, onScopeDispose, shallowRef, watch } from 'vue'
import { workbenchRequest } from '../api/workbench'
import type { WorkbenchPage, WorkbenchRun } from '../types/workbench'
export function useWorkbenchRuns(identity: () => string) {
  const rows = shallowRef<WorkbenchRun[]>([]), selected = shallowRef<WorkbenchRun>(), selectedId = shallowRef('')
  const page = shallowRef(1), total = shallowRef(0), readError = shallowRef(''), actionError = shallowRef(''), busy = shallowRef(false)
  const error = computed(() => actionError.value || readError.value)
  let alive = true, generation = 0, timer: ReturnType<typeof setTimeout> | undefined, controller: AbortController | undefined
  async function load() {
    const ticket = ++generation
    controller?.abort(); controller = new AbortController()
    try {
      const result = await workbenchRequest<WorkbenchPage>(`/runs?page=${page.value}`, undefined, 'GET', controller.signal)
      const detail = selectedId.value ? await workbenchRequest<WorkbenchRun>(`/runs/${selectedId.value}`, undefined, 'GET', controller.signal) : undefined
      if (alive && ticket === generation) { rows.value = result.rows; total.value = result.total; selected.value = detail; readError.value = '' }
    } catch (e) { if (alive && ticket === generation) readError.value = e instanceof Error ? e.message : '运行记录读取失败' }
  }
  async function act(action: () => Promise<WorkbenchRun | unknown>) {
    if (busy.value) return
    busy.value = true; actionError.value = ''
    const owner = identity()
    try {
      const result = await action() as WorkbenchRun | undefined
      if (!alive || owner !== identity()) return
      if (result?.id) { selectedId.value = result.id; selected.value = result }
      await load()
    } catch (e) { if (alive && owner === identity()) actionError.value = e instanceof Error ? e.message : '操作未完成'; await load().catch(() => {}) }
    finally { if (alive) busy.value = false }
  }
  async function poll() { if (identity() && !busy.value) await load(); if (alive) timer = setTimeout(poll, 2500) }
  watch(identity, () => { generation++;controller?.abort();rows.value=[];selected.value=undefined;selectedId.value='';page.value=1;actionError.value='';readError.value='';if(identity())void load() }, {immediate:true})
  watch([page,selectedId], () => { if (identity()) void load() })
  timer = setTimeout(poll, 2500)
  onScopeDispose(() => { alive = false; generation++; controller?.abort(); clearTimeout(timer) })
  return { rows, selected, selectedId, page, total, busy, error, load, act }
}
