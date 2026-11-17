import { javaRequest } from './sky'
import type { RouteDetail, RouteEvaluation, RouteInput, RoutePlan } from '@sky/routes'
const path = (id: string) => `/sky/tasks/${encodeURIComponent(id)}/route`
export async function getRoute(id: string): Promise<RouteDetail> { return (await javaRequest(path(id))).data }
export async function previewRoute(id: string, input: RouteInput): Promise<RouteEvaluation> { return (await javaRequest(`${path(id)}/preview`, 'POST', input)).data }
export async function saveRoute(id: string, input: RouteInput): Promise<RouteEvaluation> { return (await javaRequest(path(id), 'PUT', input)).data }
export async function getRouteVersion(id: string, version: number): Promise<RoutePlan> { return (await javaRequest(`${path(id)}/versions/${version}`)).data }

export async function suggestRoute(id: string, input: RouteInput): Promise<RouteEvaluation & { suggestedWaypoints: RouteInput['waypoints']; notice: string }> { return (await javaRequest(`${path(id)}/suggest`, 'POST', input)).data }
