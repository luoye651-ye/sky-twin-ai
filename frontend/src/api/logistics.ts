// 封装前端函数
import { javaRequest } from './sky'
import type { Audit, Track } from '@sky/sky'

// 描述后端返回的一条订单。
export interface LogisticsOrder{
    id: string
    cargoName: string
    weight: number
    startStationName: string
    endStationName: string
    status: string
    taskStatus: string
    progress: number
    deadlineAt: string
    taskId: string
    startStationId: string
    endStationId: string
    durationSeconds: number
    elapsedSeconds: number
    taskUpdatedTime: string
    taskReason: string
    aircraftId: string | null
    aircraftName: string | null
    aircraftBattery: number | null
    aircraftLongitude: number | null
    aircraftLatitude: number | null
    aircraftAltitude: number | null
    cruiseAltitude: number
    plannedSpeed: number
    createdBy: string
    createdTime: string
    deliveredBy: string | null
    deliveredAt: string | null
    serverTime: string
}

export interface LogisticsOrderDetail extends LogisticsOrder { audit: Audit[] }
export type LogisticsAction = 'assign' | 'start' | 'cancel' | 'deliver'
export interface LogisticsActionInput { reason: string; aircraftId?: string }

export async function getLogisticsOrder(id: string): Promise<LogisticsOrderDetail> {
  return (await javaRequest(`/sky/logistics/orders/${encodeURIComponent(id)}`)).data
}

export async function getLogisticsTracks(id: string): Promise<Track[]> {
  const result = await javaRequest(`/sky/logistics/orders/${encodeURIComponent(id)}/tracks`)
  if (!Array.isArray(result.data)) throw new Error('轨迹返回格式错误')
  return result.data
}

export async function operateLogisticsOrder(id: string, action: LogisticsAction, input: LogisticsActionInput): Promise<void> {
  await javaRequest(`/sky/logistics/orders/${encodeURIComponent(id)}/${action}`, 'POST', input)
}

// 请求完成后，返回订单数组。
export async function listLogisticsOrders(): Promise<LogisticsOrder[]>{
    const result = await javaRequest('/sky/logistics/orders')
    if(!Array.isArray(result.data)){
        throw new Error('订单列表返回格式错误')
    }
    return result.data
}

// 创建订单时，要发送给 Java 后端的数据。
export interface CreateLogisticsOrderInput {
    cargoName: string
    weight: number
    startStationId: string
    endStationId: string
    deadlineMinutes: number
    reason: string
  }
  
  // POST 创建订单；后端成功时返回订单编号。
  export async function createLogisticsOrder(
    input: CreateLogisticsOrderInput
  ): Promise<string> {
    const result = await javaRequest(
      '/sky/logistics/orders',
      'POST',
      input
    )
  
    return result.data
  }
  // 确认送达。失败时 javaRequest 会抛出异常。
export async function deliverLogisticsOrder(
    orderId: string,
    reason: string
  ): Promise<void> {
    await javaRequest(
      `/sky/logistics/orders/${encodeURIComponent(orderId)}/deliver`,
      'POST',
      { reason }
    )
  }
