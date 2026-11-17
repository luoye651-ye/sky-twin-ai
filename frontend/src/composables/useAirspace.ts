import { onMounted, onUnmounted, shallowRef } from 'vue'
import { getAirspaceCheck, listAirspaceChecks, listAirspaceZones, saveAirspaceZone, validateAirspace } from '../api/airspace'
import type { AirspaceCheck, AirspaceCheckRow, AirspaceZone, AirspaceZoneInput } from '@sky/airspace'

export function useAirspace(onSaved: () => Promise<void>) {
  const zones = shallowRef<AirspaceZone[]>([])
  const checks = shallowRef<AirspaceCheckRow[]>([])
  const result = shallowRef<AirspaceCheck>()
  const busy = shallowRef(false)
  const error = shallowRef('')
  const notice = shallowRef('')
  let active = true
  async function refresh() {
    try { const [nextZones, nextChecks] = await Promise.all([listAirspaceZones(), listAirspaceChecks()]); if (active) { zones.value = nextZones; checks.value = nextChecks } }
    catch (e) { if (active) error.value = e instanceof Error ? e.message : '空域数据加载失败' }
  }
  async function save(input: AirspaceZoneInput, id?: string) {
    if (busy.value) return false
    busy.value = true; error.value = ''; notice.value = ''
    try {
      await saveAirspaceZone(input, id)
      if (!active) return true
      result.value = undefined
      notice.value = '区域已保存，后续起飞将按最新规则复查。'
      await refresh()
      try { await onSaved() } catch { if (active) notice.value += ' 地图状态刷新失败，请手动刷新。' }
      return true
    } catch (e) { if (active) error.value = e instanceof Error ? e.message : '区域保存失败'; return false }
    finally { if (active) busy.value = false }
  }
  async function check(taskId: string, departureAt?: string) {
    if (busy.value) return
    busy.value = true; error.value = ''; notice.value = ''; result.value = undefined
    try { const value = await validateAirspace(taskId, departureAt); if (active) { result.value = value; await refresh() } }
    catch (e) { if (active) error.value = e instanceof Error ? e.message : '航线检查失败' }
    finally { if (active) busy.value = false }
  }
  async function open(id: string) {
    if (busy.value) return
    busy.value = true; error.value = ''
    try { const value = await getAirspaceCheck(id); if (active) result.value = value }
    catch (e) { if (active) error.value = e instanceof Error ? e.message : '检查记录读取失败' }
    finally { if (active) busy.value = false }
  }
  onMounted(() => { void refresh() })
  onUnmounted(() => { active = false })
  return { zones, checks, result, busy, error, notice, refresh, save, check, open }
}
