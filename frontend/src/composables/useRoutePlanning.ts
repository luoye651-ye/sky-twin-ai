import { computed, onUnmounted, shallowRef, watch } from 'vue'
import { getRoute, getRouteVersion, previewRoute, saveRoute, suggestRoute } from '../api/routes'
import type { RouteDetail, RouteEvaluation, RouteWaypoint, RoutePlan } from '@sky/routes'
import { routeSketch } from '../utils/taskRoute'
export function useRoutePlanning(selectedTaskId: () => string, onSave: () => Promise<void>) {
  const detail = shallowRef<RouteDetail>(), draft = shallowRef<RouteWaypoint[]>([]), result = shallowRef<RouteEvaluation>(), historical = shallowRef<RoutePlan>()
  const busy = shallowRef(false), error = shallowRef(''), notice = shallowRef(''), reason = shallowRef('人工规划绕行航线'), selected = shallowRef(-1)
  const mode = shallowRef<'navigate' | 'add' | 'move'>('navigate')
  let generation = 0, alive = true
  const editable = computed(() => !!detail.value && ['created', 'assigned'].includes(detail.value.status))
  const sketch = computed(() => detail.value ? routeSketch(historical.value ?? detail.value.plan, historical.value?.waypoints ?? draft.value, historical.value ? -1 : selected.value) : undefined)
  const dirty = computed(() => !!detail.value && JSON.stringify(draft.value) !== JSON.stringify(detail.value.plan.waypoints))
  async function load() {
    const id = selectedTaskId(), token = ++generation
    detail.value = undefined; result.value = undefined; historical.value = undefined; draft.value = []; selected.value = -1; mode.value = 'navigate'; error.value = ''; notice.value = ''
    if (!id) { busy.value = false; return }
    busy.value = true
    try { const value = await getRoute(id); if (alive && token === generation) { detail.value = value; draft.value = value.plan.waypoints.map(p => ({ ...p })) } }
    catch (e) { if (alive && token === generation) error.value = e instanceof Error ? e.message : '读取航线失败' }
    finally { if (alive && token === generation) busy.value = false }
  }
  function replace(points: RouteWaypoint[]) { if (!editable.value || busy.value || historical.value) return; draft.value = points; result.value = undefined; notice.value = '' }
  function pick(point: RouteWaypoint) {
    if (mode.value === 'add') {
      if (draft.value.length >= 24) { error.value = '最多24个中间航点'; return }
      replace([...draft.value, point]); selected.value = draft.value.length - 1
    } else if (mode.value === 'move' && selected.value >= 0) replace(draft.value.map((p, i) => i === selected.value ? point : p))
  }
  function update(index: number, point: RouteWaypoint) { replace(draft.value.map((p, i) => i === index ? point : p)) }
  function remove(index: number) { replace(draft.value.filter((_, i) => i !== index)); selected.value = -1 }
  function reorder(index: number, direction: number) { const points = [...draft.value], target = index + direction; if (target < 0 || target >= points.length) return; [points[index], points[target]] = [points[target]!, points[index]!]; replace(points); selected.value = target }
  async function evaluate(save: boolean) {
    const id = selectedTaskId(), current = detail.value, token = generation
    if (!current || busy.value || !editable.value || historical.value) return
    busy.value = true; error.value = ''; notice.value = ''
    try {
      const input = { expectedRevision: current.plan.revision, waypoints: draft.value.map(p => ({ ...p })), reason: reason.value }
      const response = await (save ? saveRoute(id, input) : previewRoute(id, input))
      if (!alive || token !== generation) return
      result.value = response
      if (save) {
        detail.value = { ...current, plan: response.plan }; draft.value = response.plan.waypoints.map(p => ({ ...p })); mode.value = 'navigate'
        notice.value = `航线 v${response.plan.revision} 已保存；起飞时仍会复查空域和资源`
        // A refresh failure must not misreport a committed route as unsaved.
        try { await onSave(); const updated = await getRoute(id); if (alive && token === generation) detail.value = updated }
        catch { if (alive && token === generation) error.value = '航线已保存，但列表刷新失败，请手动刷新' }
      }
    } catch (e) { if (alive && token === generation) error.value = e instanceof Error ? e.message : '航线校验失败' }
    finally { if (alive && token === generation) busy.value = false }
  }
  async function suggest() {
    if (!detail.value || busy.value || !editable.value || historical.value) return
    const current = detail.value, ticket = generation, id = selectedTaskId()
    busy.value = true; error.value = ''; notice.value = ''
    try {
      const value = await suggestRoute(id, { expectedRevision: current.plan.revision, waypoints: current.plan.waypoints, reason: reason.value })
      if (!alive || ticket !== generation) return
      draft.value = value.suggestedWaypoints; result.value = value; notice.value = value.notice; mode.value = 'navigate'
    } catch (e) { if (alive && ticket === generation) error.value = e instanceof Error ? e.message : '没有找到候选路线' }
    finally { if (alive && ticket === generation) busy.value = false }
  }
  async function version(revision?: number) {
    if (busy.value) return
    mode.value = 'navigate'; result.value = undefined
    if (revision == null) { historical.value = undefined; return }
    busy.value = true; const token = generation
    try { const value = await getRouteVersion(selectedTaskId(), revision); if (alive && token === generation) historical.value = value }
    catch (e) { if (alive && token === generation) error.value = String(e) }
    finally { if (alive && token === generation) busy.value = false }
  }
  watch(selectedTaskId, load, { immediate: true })
  onUnmounted(() => { alive = false; generation++ })
  return { detail, draft, result, historical, busy, error, notice, reason, selected, mode, editable, sketch, dirty, load, pick, update, remove, reorder, replace, evaluate, suggest, version }
}
