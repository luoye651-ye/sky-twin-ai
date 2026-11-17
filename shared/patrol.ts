export interface PatrolBox { classId: number; box: number[]; confidence: number; correct: boolean; matchedIou: number | null }
export interface PatrolRow { id: string; filename: string; truthCount: number; predictionCount: number; tp: number; fp: number; fn: number; precision: number | null; recall: number | null; predictions: PatrolBox[]; truths: { classId: number; box: number[] }[]; status: string }
export interface PatrolReport {
  protocolVersion: string; runId: string; modelName: string; modelSha256: string; datasetSha256: string;
  dataset: string; split: string; imageCount: number; imgsz: number; confidence: number; matchIou: number;
  tp: number; fp: number; fn: number; precision: number | null; recall: number | null; map50: number; map5095: number;
  speedMs: Record<string, number>; evaluationSeconds: number; metricNotes: string; scope: string; rows: PatrolRow[]
}
export interface PatrolRun {
  id: string; requestId: string; status: 'queued' | 'running' | 'completed' | 'failed'; stage: string; processed: number;
  modelName: string; modelSha256: string; datasetSha256: string; imageCount: number; createdBy: string; createdTime: string;
  startedTime: string | null; endedTime: string | null; errorMessage: string | null; reportSha256: string | null;
  report?: PatrolReport | null; reused?: boolean
}
export interface PatrolConfig { ready: boolean; message: string; modelName?: string; modelSha256?: string; datasetSha256?: string; imageCount?: number; confidence?: number; matchIou?: number }
export const patrolStatuses = { queued: '等待开始', running: '巡逻评测中', completed: '评测完成', failed: '评测中断' }
export const patrolStages: Record<string, string> = { queued: '等待评测', verifying: '校验模型与数据', evaluating: '模型推理与mAP计算', rendering: '生成检测图片与逐图统计', completed: '评测完成', failed: '评测中断' }
export const percentage = (value: number | null | undefined) => value == null ? '—' : `${(value * 100).toFixed(1)}%`
