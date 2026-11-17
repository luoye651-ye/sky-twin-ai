import { apiFetch } from './endpoint.ts'
import { getSkyToken, javaRequest } from './sky'
import type { PatrolConfig, PatrolRun } from '@sky/patrol'
const root = '/sky/patrol-evaluation'
export const getPatrolConfig = async (): Promise<PatrolConfig> => (await javaRequest(`${root}/config`)).data
export const getPatrolRuns = async (): Promise<PatrolRun[]> => (await javaRequest(`${root}/runs`)).data
export const getPatrolRun = async (id: string): Promise<PatrolRun> => (await javaRequest(`${root}/runs/${encodeURIComponent(id)}`)).data
export const startPatrol = async (requestId: string): Promise<PatrolRun> => (await javaRequest(`${root}/runs`, 'POST', { requestId })).data
export async function getPatrolImage(runId: string, imageId: string, kind: string): Promise<Blob> {
  const token = getSkyToken()
  const response = await apiFetch(`/java-api${root}/runs/${encodeURIComponent(runId)}/images/${encodeURIComponent(imageId)}?kind=${encodeURIComponent(kind)}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!response.ok || !response.headers.get('Content-Type')?.startsWith('image/jpeg')) throw new Error('检测图片读取失败或无权限，请重新选择图片')
  return response.blob()
}
