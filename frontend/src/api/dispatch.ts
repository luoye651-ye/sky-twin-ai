import { javaRequest } from './sky'
import type { DispatchHistory, DispatchPlan, DispatchRequest } from '@sky/dispatch'

export async function previewDispatch(input: DispatchRequest): Promise<DispatchPlan> {
  return (await javaRequest('/sky/dispatch/plans', 'POST', input)).data
}
export async function confirmDispatch(id: string, reason: string): Promise<DispatchPlan> {
  return (await javaRequest(`/sky/dispatch/plans/${encodeURIComponent(id)}/confirm`, 'POST', { reason })).data
}
export async function getDispatchHistory(): Promise<DispatchHistory[]> {
  return (await javaRequest('/sky/dispatch/plans')).data
}
export async function getDispatchPlan(id: string): Promise<DispatchPlan> {
  return (await javaRequest(`/sky/dispatch/plans/${encodeURIComponent(id)}`)).data
}
