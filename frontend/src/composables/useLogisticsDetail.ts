import { onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'
import type { Track } from '@sky/sky'
import { getLogisticsOrder, getLogisticsTracks, type LogisticsOrderDetail } from '../api/logistics'

export function useLogisticsDetail(orderId: () => string) {
  const detail = shallowRef<LogisticsOrderDetail | null>(null)
  const tracks = shallowRef<Track[]>([])
  const loading = ref(false)
  const refreshing = ref(false)
  const error = ref('')
  const trackError = ref('')
  let active = true, revision = 0
  let timer: ReturnType<typeof setInterval> | undefined

  async function refresh(initial = false) {
    const id = orderId(), current = ++revision
    if (initial) { detail.value = null; tracks.value = []; loading.value = true }
    refreshing.value = true
    const [order, points] = await Promise.allSettled([getLogisticsOrder(id), getLogisticsTracks(id)])
    if (!active || current !== revision) return
    if (order.status === 'fulfilled') { detail.value = order.value; error.value = '' }
    else error.value = order.reason instanceof Error ? order.reason.message : '详情加载失败'
    if (points.status === 'fulfilled') { tracks.value = points.value; trackError.value = '' }
    else trackError.value = points.reason instanceof Error ? points.reason.message : '轨迹加载失败'
    loading.value = false; refreshing.value = false
  }

  watch(orderId, () => { error.value = ''; trackError.value = ''; void refresh(true) }, { immediate: true })
  onMounted(() => { timer = setInterval(() => { if (!refreshing.value) void refresh() }, 3000) })
  onUnmounted(() => { active = false; revision++; clearInterval(timer) })
  return { detail, tracks, loading, refreshing, error, trackError, refresh }
}
