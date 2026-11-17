export interface AirspaceZoneInput {
  name: string; type: 'no_fly' | 'height_limit'; west: number; south: number; east: number; north: number
  minAltitude: number; maxAltitude: number; startsAt: string | null; endsAt: string | null; enabled: boolean; reason: string
}
export interface AirspaceZone extends AirspaceZoneInput {
  id: string; activeNow: boolean; createdBy: string; updatedBy: string; createdTime: string; updatedTime: string
}
export interface AirspacePoint { longitude: number; latitude: number; altitude: number; offsetSeconds: number }
export interface AirspaceViolation {
  zoneId: string; zoneName: string; type: string; phase: string; from: AirspacePoint; to: AirspacePoint
  entersAt: string; exitsAt: string; reason: string
  rule?: { west: number; south: number; east: number; north: number; minAltitude: number; maxAltitude: number; startsAt: string | null; endsAt: string | null }
}
export interface AirspaceCheck {
  taskId: string; taskTitle: string; departureAt: string; checkedAt: string; ruleRevision: number
  allowed: boolean; route: AirspacePoint[]; violations: AirspaceViolation[]
}
export interface AirspaceCheckRow {
  id: string; taskId: string; taskTitle: string; entry: string; allowed: boolean
  ruleRevision: number; departureAt: string; createdBy: string; createdTime: string
}
