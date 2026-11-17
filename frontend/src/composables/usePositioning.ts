import { computed, onMounted, onUnmounted, shallowRef, watch } from 'vue'
import type { Aircraft } from '@sky/sky'
import type { NmeaFrame, NmeaPositionResult, PositionDevice, PositionInput, PositionSample } from '@sky/positioning'
import { bindPositionDevice, listPositionDevices, postNmeaPosition, postPosition, recentPositions, setPositionMode } from '../api/positioning'
import { simulatedPosition } from '../utils/positionReplay'
import { makeBeidouDemoFrame } from '../utils/beidouDemo'
export function usePositioning(aircraft: () => Aircraft[]) {
  const devices = shallowRef<PositionDevice[]>([]), selectedId = shallowRef(''), receipts = shallowRef<PositionSample[]>([])
  const busy = shallowRef(false), sending = shallowRef(false), running = shallowRef(false), error = shallowRef(''), notice = shallowRef('')
  const senderProtocol = shallowRef<'json' | 'nmea'>('json'), nmeaFrame = shallowRef<NmeaFrame>(), nmeaResult = shallowRef<NmeaPositionResult>()
  const selected = computed(() => devices.value.find(d => d.id === selectedId.value))
  let alive = true, poll = 0, generation = 0, generator = 0, lastInput: PositionInput | undefined
  function stop() { generation++; running.value = false; window.clearTimeout(generator) }
  async function refresh() {
    const id = selectedId.value
    const next = await listPositionDevices()
    if (!alive) return
    devices.value = next
    if (!selectedId.value && next.length) selectedId.value = next[0]!.id
    if (id) { const rows = await recentPositions(id); if (alive && id === selectedId.value) receipts.value = rows }
  }
  async function act(work: () => Promise<unknown>, success: string) {
    if (busy.value) return
    busy.value = true; error.value = ''; notice.value = ''
    try { await work(); notice.value = success; await refresh() }
    catch (e) { error.value = e instanceof Error ? e.message : '定位操作失败' }
    finally { busy.value = false }
  }
  async function bind(input: { id: string; name: string; aircraftId: string }) { await act(async () => { await bindPositionDevice(input); selectedId.value = input.id }, '终端已绑定，尚未启用定位') }
  async function mode(enabled: boolean) {
    const device = selected.value; if (!device) return
    stop(); nmeaResult.value = undefined; await act(() => setPositionMode(device.id, enabled), enabled ? '终端定位已启用；飞行器暂不参与任务派机' : '终端定位已停用，恢复原任务仿真位置')
  }
  function previewNmea() {
    const device=selected.value, a=aircraft().find(value=>value.id===device?.aircraftId)
    nmeaFrame.value=makeBeidouDemoFrame({longitude:device?.longitude??a?.longitude??120.19,latitude:device?.latitude??a?.latitude??30.215,altitude:device?.altitude??240},new Date().toISOString())
    nmeaResult.value=undefined
  }
  async function send(kind: 'normal' | 'no_fix' | 'delay' | 'jump' | 'duplicate' | 'bad_checksum', point?: { longitude: number; latitude: number; altitude: number }, protocol: 'json' | 'nmea' = 'json') {
    const device = selected.value
    if (!device?.enabled || !device.sessionId || sending.value) return false
    if (kind === 'duplicate' && (!lastInput || lastInput.sessionId !== device.sessionId)) { error.value = '当前页面尚无本会话上报可重试，请先单次上报'; return false }
    const a = aircraft().find(value => value.id === device.aircraftId)
    if (!a) return false
    const input: PositionInput = kind === 'duplicate' && lastInput ? lastInput : {
      sessionId: device.sessionId, sequence: Math.max(device.lastSequence, lastInput?.sessionId === device.sessionId ? lastInput.sequence : -1) + 1, sampledAt: new Date(Date.now() - (kind === 'delay' ? 60000 : 0)).toISOString(),
      longitude: (point?.longitude ?? device.longitude ?? a.longitude) + (kind === 'jump' ? .1 : 0),
      latitude: point?.latitude ?? device.latitude ?? a.latitude, altitude: point?.altitude ?? device.altitude ?? 240, fixValid: kind !== 'no_fix',
    }
    sending.value = true; error.value = ''
    try {
      let result: PositionSample
      if (protocol === 'nmea') {
        const frame=makeBeidouDemoFrame(input,input.sampledAt,input.fixValid)
        if (kind==='bad_checksum') frame.gga=frame.gga.slice(0,-2)+(frame.gga.endsWith('00')?'01':'00')
        nmeaFrame.value=frame; nmeaResult.value=undefined
        const report=await postNmeaPosition(device.id,{...frame,sessionId:input.sessionId,sequence:input.sequence})
        if (alive && device.id === selectedId.value) nmeaResult.value=report
        result=report.receipt
      } else result = await postPosition(device.id, input)
      if (device.id === selectedId.value) {
        // Retry the normalized values, not the generator's pre-GGA rounding coordinates.
        lastInput = { ...input, sampledAt:result.sampledAt, longitude:result.longitude,latitude:result.latitude,altitude:result.altitude,fixValid:result.fixValid }
        notice.value = result.duplicate ? '相同上报重试：返回原回执，未新增记录' : `Java 回执：${result.verdict}`
        await refresh()
      }
      return true
    } catch (e) { if (alive) error.value = e instanceof Error ? e.message : '上报失败'; stop(); return false }
    finally { sending.value = false }
  }
  function start(protocol: 'json' | 'nmea' = 'json') {
    const device = selected.value, a = aircraft().find(value => value.id === device?.aircraftId)
    if (!device?.enabled || !a || sending.value) return
    stop(); const current = generation; running.value = true; senderProtocol.value=protocol
    const origin = { longitude: device.longitude ?? a.longitude, latitude: device.latitude ?? a.latitude, altitude: device.altitude ?? 240 }
    const started = performance.now()
    const step = async () => {
      if (!alive || !running.value || current !== generation) return
      await send('normal', simulatedPosition(origin, (performance.now() - started) / 1000), protocol)
      if (alive && running.value && current === generation) generator = window.setTimeout(step, 1000)
    }
    void step()
  }
  watch(selectedId, () => { stop(); receipts.value = []; lastInput = undefined; nmeaFrame.value=undefined; nmeaResult.value=undefined; void refresh().catch(e => { error.value = String(e) }) })
  onMounted(() => {
    const tick = async () => {
      try { await refresh() } catch (e) { if (alive) error.value = e instanceof Error ? e.message : '状态刷新失败' }
      if (alive) poll = window.setTimeout(tick, 2000)
    }
    void tick()
  })
  onUnmounted(() => { alive = false; stop(); window.clearTimeout(poll) })
  return { devices, selectedId, selected, receipts, busy, sending, running, error, notice, senderProtocol, nmeaFrame, nmeaResult, previewNmea, refresh, bind, mode, send, start, stop }
}
