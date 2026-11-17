import { computed, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSkyStore } from '../stores/sky'
import { javaRequest } from '../api/sky'
import type { Track } from '@sky/sky'
import { flightNavigationDisplay } from '../utils/flightNavigation'

export function useFlightNavigation() {
  const sky = useSkyStore(), route = useRoute(), router = useRouter()
  const tracks = shallowRef<Track[]>([]), trackError = shallowRef('')
  const tasks = computed(() => sky.snapshot.tasks.filter(t => t.type === 'logistics'))
  const requestedId = computed(() => typeof route.query.taskId === 'string' ? route.query.taskId : '')
  const selectedId = computed(() => requestedId.value || tasks.value.find(t => t.status === 'executing')?.id || '')
  const selected = computed(() => tasks.value.find(t => t.id === selectedId.value))
  const display = computed(() => flightNavigationDisplay(selected.value, tracks.value))
  function selectTask(id: string) { void router.replace({ query: { ...route.query, taskId: id || undefined } }) }
  // Persist automatic selection in the URL so completion does not silently switch tasks.
  watch([requestedId, tasks], ([id, values]) => {
    const running = values.find(t => t.status === 'executing')
    if (!id && running) selectTask(running.id)
  }, { immediate: true })

  watch([selectedId, () => sky.authorized, () => !!selected.value], ([id, authorized, exists], _, onCleanup) => {
    tracks.value = []; trackError.value = ''
    if (!id || !authorized || !exists) return
    let active = true, timer: ReturnType<typeof setTimeout> | undefined
    const controller = new AbortController()
    async function refresh() {
      try {
        const result = await javaRequest(`/sky/tasks/${encodeURIComponent(id)}/tracks`, 'GET', undefined, controller.signal)
        if (!Array.isArray(result.data)) throw new Error('轨迹返回格式错误')
        if (active) { tracks.value = result.data; trackError.value = '' }
      } catch (error) {
        if (active) trackError.value = error instanceof Error ? error.message : '轨迹加载失败'
      } finally {
        if (active) timer = setTimeout(refresh, 3000)
      }
    }
    void refresh()
    onCleanup(() => { active = false; clearTimeout(timer); controller.abort() })
  }, { immediate: true })
  return { tasks, selected, selectedId, requestedId, display, trackError, selectTask }
}
