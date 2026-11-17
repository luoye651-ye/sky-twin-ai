import { apiFetch } from './endpoint.ts'
import { getSkyToken } from './sky'
import { consumeAgentStream } from '../utils/agentProtocol'
import type { AgentEvent, AgentHealth } from '../types/agent'

export async function getAgentHealth(signal: AbortSignal): Promise<AgentHealth> {
  const response = await apiFetch('/agent-api/health', { signal })
  const value = await response.json().catch(() => null)
  if (!value || typeof value.ready !== 'boolean' || typeof value.message !== 'string') throw new Error('Agent服务未连接，请启动项目的agent服务。')
  return { ready: response.ok && value.ready, message: value.message }
}
export async function askAgent(question: string, requestId: string, signal: AbortSignal, onEvent: (event: AgentEvent) => void, conversationId?: string) {
  const token = getSkyToken()
  if (!token) throw new Error('请先登录平台。')
  let response: Response
  try {
    response = await apiFetch('/agent-api/chat', { method: 'POST', signal,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ question, request_id: requestId, ...(conversationId ? { conversation_id: conversationId } : {}) }) })
  } catch (error) {
    if (signal.aborted) throw error
    throw new Error('无法连接Agent服务，请检查服务状态。')
  }
  if (!response.ok) {
    const value = await response.json().catch(() => null)
    throw new Error(typeof value?.detail === 'string' ? value.detail : `助手服务暂不可用（HTTP ${response.status}）。`)
  }
  await consumeAgentStream(response, onEvent)
}
