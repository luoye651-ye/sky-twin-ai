import { onMounted, onUnmounted, shallowRef } from 'vue'
import { cancelTraffic, confirmTraffic, getTraffic, getTrafficPlan, previewTraffic } from '../api/traffic'
import type { TrafficPlan, TrafficRequest, TrafficState } from '@sky/traffic'
export function useTrafficPlanning(refreshSky: () => Promise<void>) {
  const state = shallowRef<TrafficState>(), plan = shallowRef<TrafficPlan>(), busy = shallowRef(false), error = shallowRef(''), notice = shallowRef('')
  let alive = true, timer: ReturnType<typeof setTimeout> | undefined, generation = 0, reading = false
  async function refresh() {
    if (reading) return
    reading = true
    try { const value = await getTraffic(); if (alive) state.value = value }
    catch (e) { if (alive) error.value = e instanceof Error ? e.message : '读取协同时钟失败' }
    finally { reading = false }
  }
  async function poll() { await refresh(); if (alive) timer = setTimeout(poll, 3000) }
  function invalidate() { if (busy.value) return; generation++; plan.value = undefined; notice.value = '' }
  async function action(work: () => Promise<TrafficPlan | void>, success: string) {
    if (busy.value) return
    busy.value = true; error.value = ''; notice.value = ''; const token = ++generation
    try {
      const value = await work()
      if (!alive || token !== generation) return
      if (value) plan.value = value
      notice.value = success
      try { await Promise.all([refresh(), refreshSky()]) }
      catch { if (alive) error.value = '操作已成功，但任务列表刷新失败，请手动刷新' }
    } catch (e) { if (alive && token === generation) error.value = e instanceof Error ? e.message : '协同操作失败' }
    finally { if (alive && token === generation) busy.value = false }
  }
  const preview = (request: TrafficRequest) => action(() => previewTraffic(request), '预览已生成，尚未预约；确认后才会自动起飞')
  const confirm = (reason: string) => plan.value ? action(() => confirmTraffic(plan.value!.id, reason), '预约已确认；Java 将在仿真时刻到达后复查并自动起飞') : Promise.resolve()
  const cancel = (taskId: string, reason: string) => action(() => cancelTraffic(taskId, reason), '预约已取消，任务仍为已分配，可修改航线或重新预约')
  const load = (id: string) => action(() => getTrafficPlan(id), '已读取历史方案；表格下方显示当前预约状态')
  onMounted(poll)
  onUnmounted(() => { alive = false; generation++; clearTimeout(timer) })
  return { state, plan, busy, error, notice, refresh, invalidate, preview, confirm, cancel, load }
}
