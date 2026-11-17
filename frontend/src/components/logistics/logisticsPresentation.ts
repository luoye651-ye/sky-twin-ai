import type { LogisticsOrder } from '../../api/logistics'

export const actionLabels = { assign: '分配货运无人机', start: '执行仿真', cancel: '取消配送', deliver: '确认送达' }

export function deliveryStage(order: LogisticsOrder): string {
  if (order.status === 'delivered') return '已送达'
  return ({ created: '待分配', assigned: '待起飞', executing: '运输中', completed: '待确认送达',
    cancelled: '已取消', failed: '配送失败' } as Record<string, string>)[order.taskStatus] ?? order.taskStatus
}

export function formatTime(value?: string | null): string {
  if (!value) return '—'
  const time = new Date(value)
  return Number.isNaN(time.getTime()) ? value : time.toLocaleString('zh-CN', { hour12: false })
}

export function isOverdue(order: LogisticsOrder): boolean {
  const reference = ['completed', 'failed', 'cancelled'].includes(order.taskStatus)
    ? order.taskUpdatedTime : order.serverTime
  return Number.isFinite(Date.parse(reference)) && Date.parse(reference) > Date.parse(order.deadlineAt)
}
