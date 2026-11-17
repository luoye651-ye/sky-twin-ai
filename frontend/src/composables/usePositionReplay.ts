import { computed, onUnmounted, shallowRef } from 'vue'
import { queryPositions } from '../api/positioning'
import type { PositionSample } from '@sky/positioning'
import { replayPoint } from '../utils/positionReplay'
export function usePositionReplay() {
  const points = shallowRef<PositionSample[]>([])
  const active = shallowRef(false), playing = shallowRef(false), loading = shallowRef(false)
  const offset = shallowRef(0), speed = shallowRef(1), error = shallowRef(''), hasMore = shallowRef(false)
  let request = 0, frame = 0, last = 0
  const begin = computed(() => points.value.length ? Date.parse(points.value[0]!.sampledAt) : 0)
  const duration = computed(() => points.value.length ? Math.max(0, Date.parse(points.value[points.value.length - 1]!.sampledAt) - begin.value) : 0)
  const at = computed(() => begin.value + offset.value)
  const position = computed(() => replayPoint(points.value, at.value))
  function pause() { playing.value = false; cancelAnimationFrame(frame) }
  function reset() { request++; pause(); points.value = []; active.value = false; offset.value = 0; hasMore.value = false; loading.value = false; error.value = '' }
  async function load(id: string, from: string, to: string) {
    reset(); const generation = ++request; loading.value = true
    try {
      const collected: PositionSample[] = []; let cursor = 0
      // Explicit cap keeps the browser bounded; never silently call a truncated route complete.
      for (let page = 0; page < 5; page++) {
        const result = await queryPositions(id, from, to, cursor)
        if (generation !== request) return
        collected.push(...result.rows); cursor = result.nextCursor; hasMore.value = result.hasMore
        if (!result.hasMore) break
      }
      points.value = collected.sort((a, b) => Date.parse(a.sampledAt) - Date.parse(b.sampledAt) || a.id - b.id)
      active.value = !!points.value.length
      if (!active.value) error.value = '所选时间段没有通过校验的定位点'
    } catch (e) { if (generation === request) error.value = e instanceof Error ? e.message : '回放查询失败' }
    finally { if (generation === request) loading.value = false }
  }
  function play() {
    if (!active.value || !duration.value) return
    if (offset.value >= duration.value) offset.value = 0
    pause(); playing.value = true; last = performance.now()
    const step = (now: number) => {
      offset.value = Math.min(duration.value, offset.value + (now - last) * speed.value); last = now
      if (offset.value >= duration.value) pause()
      else frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
  }
  function seek(value: number) { offset.value = Math.max(0, Math.min(duration.value, value)) }
  onUnmounted(reset)
  return { points, active, playing, loading, offset, speed, error, hasMore, duration, at, position, load, play, pause, reset, seek }
}
