import type { VisionChatResult } from './visionChat'
export interface AgentMapTarget { kind: 'aircraft' | 'task'; id: string; label: string }
export interface AgentSource {
  citation_id: string; source: string; section: string; text?: string; version?: string
  line_start: number; line_end: number; code_references: string[]
}
export interface AgentAnswer {
  dispatch_plan_id?: string | null
  map_targets?: AgentMapTarget[]
  text: string; tool_messages: number; mcp_calls: number
  aircraft_count: number | null; knowledge_calls: number; sources: AgentSource[]
}
export type AgentEvent = { type: 'progress'; message: string } | { type: 'answer'; data: AgentAnswer } | { type: 'error'; message: string } | { type: 'heartbeat' }
export interface AgentHealth { ready: boolean; message: string }
export interface AgentMessage {
  id: string; role: 'user' | 'assistant'; state: 'pending' | 'complete' | 'error' | 'stopped'
  text: string; progress: string[]; answer?: AgentAnswer
  vision?: VisionChatResult
}
