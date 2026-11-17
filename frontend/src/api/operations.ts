import { apiFetch } from './endpoint.ts'
import { javaRequest, getSkyToken } from './sky'
export type OpsRow = Record<string, unknown>
export interface OpsPage { rows: OpsRow[]; total: number; page: number; size: number }
const root = '/sky/operations'
export const opsRead = async <T>(path: string, signal?: AbortSignal): Promise<T> => (await javaRequest(root + path, 'GET', undefined, signal)).data
export const opsWrite = async <T = OpsRow>(path: string, input: unknown = {}, method = 'POST'): Promise<T> => (await javaRequest(root + path, method, input)).data
export const valueText = (row: OpsRow, key: string) => row[key] == null ? '—' : String(row[key])
export const valueNumber = (row: OpsRow, key: string) => Number(row[key] ?? 0)
export async function exportOpsReport(id: string, format: 'txt' | 'html') {
  const token = getSkyToken()
  const response = await apiFetch(`/java-api${root}/reports/${encodeURIComponent(id)}/export?format=${format}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!response.ok || response.headers.get('Content-Type')?.includes('json')) throw new Error('报告导出失败或无权限')
  const url = URL.createObjectURL(await response.blob()), link = document.createElement('a')
  link.href = url; link.download = `${id}.${format}`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
}
