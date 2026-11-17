import { onScopeDispose, shallowRef, watch } from 'vue'
import { opsRead, type OpsRow, type OpsPage } from '../api/operations'
export function useOperationPage(path: () => string) {
  const rows = shallowRef<OpsRow[]>([]), total = shallowRef(0), page = shallowRef(1), size = 20
  const busy = shallowRef(false), error = shallowRef(''), notice = shallowRef('')
  let alive = true, sequence = 0, controller: AbortController | undefined
  async function load() {
    const ticket = ++sequence; controller?.abort(); controller = new AbortController(); busy.value = true; error.value = ''
    try {
      const endpoint = path(), data = await opsRead<OpsPage>(`${endpoint}${endpoint.includes('?') ? '&' : '?'}page=${page.value}&size=${size}`, controller.signal)
      if (alive && ticket === sequence) { rows.value = data.rows; total.value = data.total }
    } catch (e) { if (alive && ticket === sequence) error.value = e instanceof Error ? e.message : '记录读取失败' }
    finally { if (alive && ticket === sequence) busy.value = false }
  }
  async function act(action: () => Promise<unknown>) {
    if (busy.value) return false
    busy.value = true; error.value = ''; notice.value = ''
    try { await action(); if (alive) { if (!notice.value) notice.value = '操作已保存'; await load() }; return true }
    catch (e) { if (alive) error.value = e instanceof Error ? e.message : '操作未完成'; return false }
    finally { if (alive) busy.value = false }
  }
  watch([path, page], () => { void load() }, { immediate: true })
  onScopeDispose(() => { alive = false; sequence++; controller?.abort() })
  return { rows, total, page, size, busy, error, notice, load, act }
}
