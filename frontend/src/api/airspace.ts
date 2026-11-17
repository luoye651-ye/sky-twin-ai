import { javaRequest } from './sky'
import type { AirspaceCheck, AirspaceCheckRow, AirspaceZone, AirspaceZoneInput } from '@sky/airspace'
export async function listAirspaceZones(): Promise<AirspaceZone[]> { return (await javaRequest('/sky/airspace/zones')).data }
export async function saveAirspaceZone(input: AirspaceZoneInput, id?: string): Promise<string> {
  return (await javaRequest(`/sky/airspace/zones${id ? `/${encodeURIComponent(id)}` : ''}`, id ? 'PUT' : 'POST', input)).data
}
export async function validateAirspace(taskId: string, departureAt?: string): Promise<AirspaceCheck> {
  return (await javaRequest('/sky/airspace/validate', 'POST', { taskId, departureAt: departureAt || null })).data
}
export async function listAirspaceChecks(): Promise<AirspaceCheckRow[]> { return (await javaRequest('/sky/airspace/checks')).data }
export async function getAirspaceCheck(id: string): Promise<AirspaceCheck> { return (await javaRequest(`/sky/airspace/checks/${encodeURIComponent(id)}`)).data.result }
