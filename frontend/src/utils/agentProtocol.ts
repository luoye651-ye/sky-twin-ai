import type { AgentAnswer, AgentEvent, AgentSource } from '../types/agent'

function object(value: unknown): value is Record<string, unknown> { return value !== null && typeof value === 'object' && !Array.isArray(value) }
function count(value: unknown): value is number { return Number.isSafeInteger(value) && (value as number) >= 0 }
function source(value: unknown): value is AgentSource {
  return object(value) && typeof value.citation_id === 'string' && /^K\d+$/.test(value.citation_id)
    && (value.text === undefined || (typeof value.text === 'string' && value.text.length <= 1000))
    && typeof value.source === 'string' && typeof value.section === 'string' && count(value.line_start) && count(value.line_end)
    && Array.isArray(value.code_references) && value.code_references.every(item => typeof item === 'string')
}
function answer(value: unknown): value is AgentAnswer {
  return object(value) && typeof value.text === 'string' && count(value.tool_messages) && count(value.mcp_calls)
    && (value.dispatch_plan_id == null || (typeof value.dispatch_plan_id === 'string' && /^DP-[a-f0-9]{32}$/.test(value.dispatch_plan_id)))
    && (value.map_targets === undefined || (Array.isArray(value.map_targets) && value.map_targets.length <= 20 && value.map_targets.every(item => object(item) && ['aircraft', 'task'].includes(String(item.kind)) && typeof item.id === 'string' && item.id.length <= 40 && typeof item.label === 'string' && item.label.length <= 100)))
    && count(value.knowledge_calls) && (value.aircraft_count === null || count(value.aircraft_count))
    && Array.isArray(value.sources) && value.sources.length <= 9 && value.sources.every(source)
}
export function decodeAgentEvent(line: string): AgentEvent {
  let value: unknown
  try { value = JSON.parse(line) } catch { throw new Error('助手返回格式异常，请稍后重试。') }
  if (object(value)) {
    if (value.type === 'heartbeat') return { type: 'heartbeat' }
    if ((value.type === 'progress' || value.type === 'error') && typeof value.message === 'string') return { type: value.type, message: value.message }
    if (value.type === 'answer' && answer(value.data)) return { type: 'answer', data: value.data }
  }
  throw new Error('助手返回的数据结构异常。')
}
export async function consumeAgentStream(response: Response, onEvent: (event: AgentEvent) => void): Promise<void> {
  if (!response.body) throw new Error('浏览器不支持读取助手响应。')
  const reader = response.body.getReader(), decoder = new TextDecoder('utf-8', { fatal: true })
  let buffer = '', finished = false
  const accept = (line: string) => {
    if (!line.trim()) return
    if (finished) throw new Error('助手在最终答复后返回了多余数据。')
    const event = decodeAgentEvent(line)
    if (event.type === 'error') throw new Error(event.message)
    onEvent(event)
    if (event.type === 'answer') finished = true
  }
  try {
    while (true) {
      const part = await reader.read()
      buffer += decoder.decode(part.value, { stream: !part.done })
      if (buffer.length > 131072) throw new Error('助手响应过大，已停止读取。')
      let position: number
      while ((position = buffer.indexOf('\n')) !== -1) { accept(buffer.slice(0, position)); buffer = buffer.slice(position + 1) }
      if (part.done) break
    }
    if (buffer.trim()) accept(buffer)
    if (!finished) throw new Error('助手连接提前结束，未收到完整答复。')
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock() }
}
