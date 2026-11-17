import { javaRequest } from './sky'
import type { NmeaPositionInput, NmeaPositionResult, PositionDevice, PositionInput, PositionPage, PositionSample } from '@sky/positioning'
const root = '/sky/positioning/devices'
export async function listPositionDevices(): Promise<PositionDevice[]> { return (await javaRequest(root)).data }
export async function bindPositionDevice(input: { id: string; name: string; aircraftId: string }): Promise<string> { return (await javaRequest(root, 'POST', input)).data }
export async function setPositionMode(id: string, enabled: boolean): Promise<PositionDevice> { return (await javaRequest(`${root}/${encodeURIComponent(id)}/mode`, 'POST', { enabled, reason: enabled ? '启用电脑仿真终端定位' : '停用终端定位，恢复任务仿真位置' })).data }
export async function postPosition(id: string, input: PositionInput): Promise<PositionSample> { return (await javaRequest(`${root}/${encodeURIComponent(id)}/samples`, 'POST', input)).data }
export async function postNmeaPosition(id: string, input: NmeaPositionInput): Promise<NmeaPositionResult> { return (await javaRequest(`${root}/${encodeURIComponent(id)}/nmea-samples`, 'POST', input)).data }
export async function recentPositions(id: string): Promise<PositionSample[]> { return (await javaRequest(`${root}/${encodeURIComponent(id)}/recent`)).data }
export async function queryPositions(id: string, from: string, to: string, after = 0): Promise<PositionPage> {
  return (await javaRequest(`${root}/${encodeURIComponent(id)}/samples?${new URLSearchParams({ from, to, after: String(after), limit: '1000' })}`)).data
}
