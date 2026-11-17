export type ConnectionState = 'disabled' | 'waiting' | 'online' | 'stale' | 'offline'
export interface PositionDevice {
  id: string; name: string; aircraftId: string; aircraftName: string; source: 'simulated_terminal'
  enabled: boolean; sessionId: string | null; lastSequence: number; latestSampleId: number | null
  sampledAt: string | null; receivedAt: string | null; longitude: number | null; latitude: number | null
  altitude: number | null; connectionState: ConnectionState; serverTime: string
}
export interface PositionInput {
  sessionId: string; sequence: number; sampledAt: string; longitude: number; latitude: number; altitude: number; fixValid: boolean
}
export interface NmeaFrame { gga: string; utcDate: string; takeoffAltitudeMsl: number }
export interface NmeaPositionInput extends NmeaFrame { sessionId: string; sequence: number }
export interface NmeaPositionResult {
  simulation: true; source: 'simulated_terminal'; receipt: PositionSample
  decoded: { talker: string; constellation: string; sampledAt: string; longitude: number; latitude: number
    altitudeMsl: number; takeoffAltitudeMsl: number; relativeAltitude: number; quality: number; satellites: number; hdop: number; fixValid: boolean }
}
export interface PositionSample {
  id: number; deviceId: string; sessionId: string; sequenceNo: number; sampledAt: string; receivedAt: string
  longitude: number; latitude: number; altitude: number; fixValid: boolean; accepted: boolean
  verdict: string; source: 'simulated_terminal'; altitudeReference: 'relative_to_takeoff'; duplicate?: boolean
}
export interface PositionPage { rows: PositionSample[]; hasMore: boolean; nextCursor: number; serverTime: string }
export const connectionLabels: Record<ConnectionState, string> = { disabled: '已停用', waiting: '等待定位', online: '定位新鲜', stale: '定位过期（>5秒）', offline: '定位离线（>30秒）' }
export const verdictLabels: Record<string, string> = { accepted: '接收', no_fix: '无有效定位', stale_timestamp: '采样延迟超过30秒', future_timestamp: '采样时间超前', out_of_order_sequence: '序号乱序', out_of_order_timestamp: '采样时间乱序', position_jump: '位置突跳', invalid_coordinates: '无效坐标' }
