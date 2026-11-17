import { javaRequest } from './sky'
import type { TrafficPlan, TrafficRequest, TrafficState } from '@sky/traffic'
export async function getTraffic(): Promise<TrafficState> { return (await javaRequest('/sky/traffic')).data }
export async function getTrafficPlan(id: string): Promise<TrafficPlan> { return (await javaRequest(`/sky/traffic/plans/${encodeURIComponent(id)}`)).data }
export async function previewTraffic(input: TrafficRequest): Promise<TrafficPlan> { return (await javaRequest('/sky/traffic/plans', 'POST', input)).data }
export async function confirmTraffic(id: string, reason: string): Promise<TrafficPlan> { return (await javaRequest(`/sky/traffic/plans/${encodeURIComponent(id)}/confirm`, 'POST', { reason })).data }
export async function cancelTraffic(id: string, reason: string): Promise<void> { await javaRequest(`/sky/traffic/slots/${encodeURIComponent(id)}/cancel`, 'POST', { reason }) }
