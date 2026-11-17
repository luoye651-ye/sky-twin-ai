import type { AgentAnswer } from './agent'
import type { VisionChatResult } from './visionChat'
export interface RunSpan {
  id: string; parent_id: string | null; kind: string; name: string; status: string
  started: number; ended: number | null; input_tokens: number | null; output_tokens: number | null; summary: string
  arguments?: Record<string,unknown>
}
export interface EvaluationRow {
  id: string; category: string; variant: string; passed: boolean; latency_ms: number; metric: string
  text?: string; error?: string; sections?: string[]; tools?: string[]; requires_human_review?: boolean
}
export interface WorkbenchRun {
  id: string; kind: string; status: string; revision: number; created: number; updated: number
  input: { question?: string; mode?: string; evaluation_mode?: string; source_kind?: string; source_id?: string; compare_id?: string; parent_id?: string }
  checkpoint: { step?: string; message?: string; mode?: string; answer?: AgentAnswer; evidence?: Record<string, unknown>; retrieval?: Record<string, unknown>[]; versions?: Record<string, unknown>; plan_id?: string; rows?: EvaluationRow[];response?:VisionChatResult }
  spans?: RunSpan[]
  metrics?: { model_calls: number; tool_calls: number; input_tokens: number | null; output_tokens: number | null; estimated_cost: number | null; duration_ms: number; usage_complete: boolean }
}
export interface KnowledgeDocument { id: string; name: string; version: number; sha256: string; status: string; chunk_count: number; error: string; created: number }
export interface EvaluationCase { id: string; category: string; question: string; section?: string; tools: string[]; terms: string[]; refusal?: boolean }
export interface WorkbenchPage { rows: WorkbenchRun[]; total: number; page: number }
export interface RunInput { question: string; mode: 'demo' | 'live'; external_allowed: boolean; source_kind: 'none' | 'task' | 'event' | 'analysis'; source_id: string; compare_id: string; parent_id: string }
