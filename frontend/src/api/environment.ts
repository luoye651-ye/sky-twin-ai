import { apiFetch } from './endpoint.ts'
import { getSkyToken, javaRequest } from './sky'
import type { DiscoveryDetail, DiscoveryInput, DiscoverySummary, EnvironmentalReport, EnvironmentalReportSummary, VisionAnalysis } from '@sky/environment'
const root = '/sky/environment'
export async function analyzeEvidence(file: File, requestId: string): Promise<VisionAnalysis> {
  const form = new FormData(), token = getSkyToken()
  form.append('image', file)
  const response = await apiFetch(`/java-api${root}/analyses?requestId=${encodeURIComponent(requestId)}`, { method: 'POST', headers: token ? { Authorization: `Bearer ${token}` } : {}, body: form })
  const value = await response.json().catch(() => null)
  if (!response.ok || value?.code !== 200) throw new Error(value?.msg || '影像分析未完成；如响应中断，请勿假定成功')
  return value.data
}
export async function getDiscoveries(status?: string): Promise<DiscoverySummary[]> { return (await javaRequest(`${root}/discoveries${status ? `?status=${encodeURIComponent(status)}` : ''}`)).data }
export async function getDiscovery(id: string): Promise<DiscoveryDetail> { return (await javaRequest(`${root}/discoveries/${encodeURIComponent(id)}`)).data }
async function multipart(path: string, input: unknown, file: File): Promise<DiscoveryDetail> {
  const form = new FormData(), token = getSkyToken()
  form.append('input', new Blob([JSON.stringify(input)], { type: 'application/json' }))
  form.append('image', file)
  const response = await apiFetch(`/java-api${root}${path}`, { method: 'POST', headers: token ? { Authorization: `Bearer ${token}` } : {}, body: form })
  let result
  try { result = await response.json() } catch { throw new Error(`影像上传响应异常（HTTP ${response.status}），请检查文件大小和服务状态`) }
  if (!response.ok || result.code !== 200) throw new Error(result.msg || '影像提交失败')
  return result.data
}
export const createDiscovery = (input: DiscoveryInput, file: File) => multipart('/discoveries', input, file)
export async function reviewDiscovery(id: string, input: { decision: 'confirm' | 'reject'; severity: string; reason: string }): Promise<DiscoveryDetail> { return (await javaRequest(`${root}/discoveries/${encodeURIComponent(id)}/review`, 'POST', input)).data }
export async function createEnvironmentalResponse(id: string, input: { startStationId: string; endStationId: string; reason: string }): Promise<DiscoveryDetail> { return (await javaRequest(`${root}/discoveries/${encodeURIComponent(id)}/responses`, 'POST', input)).data }
export const closeDiscovery = (id: string, resolution: string, image: File) => multipart(`/discoveries/${encodeURIComponent(id)}/close`, { resolution }, image)
export async function getEvidenceImage(id: string, after = false): Promise<Blob> {
  const token = getSkyToken(), response = await apiFetch(`/java-api${root}/discoveries/${encodeURIComponent(id)}/image?after=${after}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!response.ok || !response.headers.get('Content-Type')?.startsWith('image/')) throw new Error('证据图片读取失败或无权限')
  return response.blob()
}
export async function getEnvironmentalReports(): Promise<EnvironmentalReportSummary[]> { return (await javaRequest(`${root}/reports`)).data }
export async function getEnvironmentalReport(id: string): Promise<EnvironmentalReport> { return (await javaRequest(`${root}/reports/${encodeURIComponent(id)}`)).data }
