import { apiFetch } from './endpoint.ts'
import { getSkyToken } from './sky'
export async function workbenchRequest<T>(path: string, input?: unknown, method = 'GET', signal?: AbortSignal): Promise<T> {
  const token = getSkyToken()
  if (!token) throw new Error('请先登录平台')
  const form = input instanceof FormData
  const response = await apiFetch('/agent-api/workbench' + path, { method, signal,
    headers: { Authorization: `Bearer ${token}`, ...(!form && input !== undefined ? { 'Content-Type': 'application/json' } : {}) },
    body: input === undefined ? undefined : form ? input : JSON.stringify(input) })
  const value = await response.json().catch(() => null)
  if (!response.ok || value === null) throw new Error(typeof value?.detail === 'string' ? value.detail : `AI工作台请求失败（${response.status}）`)
  return value as T
}
export function downloadArtifact(value: unknown, filename: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json;charset=utf-8' }))
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
