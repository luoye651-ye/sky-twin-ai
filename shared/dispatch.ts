export interface DispatchSelection { taskId: string; priority: number }
export interface DispatchRequest { tasks: DispatchSelection[]; aircraftIds?: string[] }
export interface DispatchCandidate {
  aircraftId: string; aircraftName: string; eligible: boolean; reasons: string[]
  distanceMeters: number; expectedEnergy: number; remainingBattery: number
  distanceCost: number; batteryCost: number; capacityCost: number; cost: number; score: number
}
export interface DispatchAssignment {
  taskId: string; taskTitle: string; priority: number; aircraftId: string; aircraftName: string
  distanceMeters: number; expectedEnergy: number; remainingBattery: number; cost: number; score: number
}
export interface DispatchDecision {
  taskId: string; taskTitle: string; type: string; priority: number; aircraftId: string | null
  explanation: string; candidates: DispatchCandidate[]
}
export interface DispatchMetrics {
  assignedCount: number; priorityTotal: number; totalDistanceMeters: number
  totalExpectedEnergy: number; totalCost: number
}
export interface DispatchResult {
  algorithm: string; assignments: DispatchAssignment[]; decisions: DispatchDecision[]
  optimized: DispatchMetrics; baseline: DispatchMetrics; calculationMs: number
}
export interface DispatchHistory {
  id: string; algorithm: string; status: 'proposed' | 'confirmed'; createdBy: string
  createdTime: string; expiresAt: string; confirmedBy: string | null; confirmedAt: string | null; reason: string | null
}
export interface DispatchPlan extends DispatchHistory {
  request: DispatchRequest; result: DispatchResult; serverTime: string
}
