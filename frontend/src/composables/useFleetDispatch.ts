import { computed, onMounted, onUnmounted, shallowRef } from 'vue'
import { confirmDispatch, getDispatchHistory, getDispatchPlan, previewDispatch } from '../api/dispatch'
import type { DispatchHistory, DispatchPlan, DispatchRequest } from '@sky/dispatch'

export function useFleetDispatch(onAssigned: () => Promise<void>) {
  const plan = shallowRef<DispatchPlan>()
  const history = shallowRef<DispatchHistory[]>([])
  const busy = shallowRef(false)
  const error = shallowRef('')
  const notice = shallowRef('')
  const remainingSeconds = shallowRef(0)
  let active = true
  let expiresAt = 0
  let timer: ReturnType<typeof setInterval> | undefined
  const canConfirm = computed(() => !!plan.value && plan.value.status === 'proposed'
    && remainingSeconds.value > 0 && plan.value.result.assignments.length > 0 && !busy.value)
  function accept(value: DispatchPlan) {
    plan.value = value
    expiresAt = Date.now() + Math.max(0, Date.parse(value.expiresAt) - Date.parse(value.serverTime))
    remainingSeconds.value = Math.max(0, Math.ceil((expiresAt - Date.now()) / 1000))
  }
  async function loadHistory() {
    try { const value = await getDispatchHistory(); if (active) history.value = value }
    catch (e) { if (active) error.value = e instanceof Error ? e.message : '调度历史加载失败' }
  }
  async function generate(input: DispatchRequest) {
    if (busy.value) return
    busy.value = true; error.value = ''; notice.value = ''; plan.value = undefined
    try {
      const value = await previewDispatch(input)
      if (active) { accept(value); await loadHistory() }
    } catch (e) { if (active) error.value = e instanceof Error ? e.message : '方案生成失败' }
    finally { if (active) busy.value = false }
  }
  async function open(id: string) {
    if (busy.value) return
    busy.value = true; error.value = ''; notice.value = ''
    try { const value = await getDispatchPlan(id); if (active) accept(value) }
    catch (e) { if (active) error.value = e instanceof Error ? e.message : '方案读取失败' }
    finally { if (active) busy.value = false }
  }
  async function confirm(reason: string) {
    if (!canConfirm.value || !plan.value) return false
    busy.value = true; error.value = ''; notice.value = ''
    try {
      const value = await confirmDispatch(plan.value.id, reason)
      if (!active) return true
      accept(value)
      notice.value = `已分配 ${value.result.assignments.length} 个任务，可前往任务管理执行仿真。`
      // A refresh failure must not make a successful batch look like a failed assignment.
      try { await onAssigned() }
      catch { if (active) notice.value += ' 状态刷新失败，请手动刷新任务列表。' }
      await loadHistory()
      return true
    } catch (e) {
      if (active) error.value = (e instanceof Error ? e.message : '批量派机失败') + '；请刷新任务或重新生成方案。'
      return false
    } finally { if (active) busy.value = false }
  }
  onMounted(() => {
    void loadHistory()
    timer = setInterval(() => { remainingSeconds.value = Math.max(0, Math.ceil((expiresAt - Date.now()) / 1000)) }, 1000)
  })
  onUnmounted(() => { active = false; clearInterval(timer) })
  return { plan, history, busy, error, notice, remainingSeconds, canConfirm, generate, confirm, open, loadHistory }
}
